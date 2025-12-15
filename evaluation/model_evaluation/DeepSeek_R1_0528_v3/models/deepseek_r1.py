# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

from typing import Any
import json
import urllib.parse
import requests
import time
import sys
import html2text
import os


_CORPINFO_CACHE: dict[str, str] = {}


def _raw_corpinfo_to_sections(response: dict[str, Any]) -> dict[str, str]:
    # Attributes
    attributes = "Corpus attributes:\n"
    for attrib in response.get("attributes", []):
        name = attrib.get("name", "")
        label = attrib.get("label") or name
        attributes += f'structure "{name}" which represents "{label}"\n'

    # Annotations
    annotations = "Corpus annotations:\n"
    for annot in response.get("wposlist", []):
        if len(annot) >= 2:
            annotations += f'annotation "{annot[0]}" is "{annot[1]}"\n'

    # Full tagset description
    tagsetdoc_url = response.get("tagsetdoc") or ""
    annotations_full = ""
    if tagsetdoc_url:
        try:
            resp = requests.get(tagsetdoc_url, timeout=10)
            if resp.status_code == 200:
                h2t = html2text.HTML2Text()
                h2t.ignore_links = True
                annotations_full = h2t.handle(resp.text)
            else:
                annotations_full = tagsetdoc_url
        except Exception:
            annotations_full = tagsetdoc_url

    # Lempos suffixes
    lempos_suffixes = "Lempos suffixes:\n"
    for annot in response.get("lposlist", []):
        if len(annot) >= 2:
            lempos_suffixes += f'lempos "{annot[0]}" is "{annot[1]}"\n'

    # Structures + Attributes
    structures_and_attributes = "Following structures and attributes are present in the corpus:\n"
    for struct in response.get("structures", []):
        struct_name = struct.get("name", "")
        struct_label = struct.get("label") or struct_name
        structures_and_attributes += f'structure "{struct_name}" which represents "{struct_label}"\n'
        for atrib in struct.get("attributes", []):
            atrib_name = atrib.get("name", "")
            atrib_label = atrib.get("label") or atrib_name
            structures_and_attributes += (
                f'structure "{struct_name}" has attribute "{atrib_name}" '
                f'which represents "{atrib_label}"\n'
            )

    # Gramrels
    gramrels_list = ["Possible word sketch relations:"]
    for g in response.get("gramrels", []):
        if isinstance(g, str):
            gramrels_list.append(g)
    gramrels = "\n".join(gramrels_list)

    # Language
    lang = response.get("lang")
    if lang:
        language = f"The corpus is in {lang} language.\n"
    else:
        language = ""

    return {
        "attributes": attributes,
        "annotations": annotations,
        "annotations_full": annotations_full,
        "lempos_suffixes": lempos_suffixes,
        "structures_and_attributes": structures_and_attributes,
        "language": language,
        "gramrels": gramrels,
    }


def _compress_corpinfo_with_deepseek(corpus_text: str, api_key: str) -> str:
    if not corpus_text.strip() or not api_key:
        return corpus_text

    messages = [
        {
            "role": "system",
            "content": (
                "You rewrite corpus metadata into a concise but detailed description that helps "
                "another model write correct Sketch Engine CQL queries. Focus on:\n"
                "- POS tags and their meanings\n"
                "- lempos suffixes\n"
                "- available attributes and structures\n"
                "- grammatical relations (word sketch relations)\n"
                "- any language-specific quirks that influence CQL\n"
                "Keep all technical details, but remove redundancy. Reply with plain text only."
            ),
        },
        {
            "role": "user",
            "content": (
                "Rewrite the following corpus description into a concise summary (max ~4000 characters). "
                "Preserve all information needed to write correct CQL for this corpus. "
                "Do NOT use markdown or code fences.\n\n"
                + corpus_text
            ),
        },
    ]

    try:
        summary = call_einfra(messages, api_key)
        summary = summary.strip()
        return summary or corpus_text
    except Exception:
        return corpus_text


def get_corpinfo_prompt_cached(
    corpname: str,
    corpinfo: dict[str, Any],
    api_key_einfra: str,
) -> str:
    if corpname == "__other__":
        return ""

    if corpname in _CORPINFO_CACHE:
        return _CORPINFO_CACHE[corpname]

    sections = _raw_corpinfo_to_sections(corpinfo)

    full_text = (
        sections["language"]
        + "\n"
        + sections["attributes"]
        + "\n"
        + sections["structures_and_attributes"]
        + "\n"
        + sections["annotations"]
        + "\n"
        + sections["lempos_suffixes"]
        + "\n"
        + sections["gramrels"]
        + "\n\nFull tagset documentation:\n"
        + sections["annotations_full"]
    )

    compact = _compress_corpinfo_with_deepseek(full_text, api_key_einfra)
    _CORPINFO_CACHE[corpname] = compact
    return compact


def shorten_prompt(prompt):
    lens = []
    for i, content in enumerate(prompt):
        if i == 0:
            continue
        if content.get("role") == "assistant":
            lens.append((len(content.get("content", "")), i))

    if not lens:
        print("shorten_prompt: nothing to shorten.", file=sys.stderr)
        return

    _, idx = sorted(lens)[-1]

    prompt.pop(idx)

    if idx - 1 > 0 and prompt[idx - 1].get("role") == "user":
        prompt.pop(idx - 1)

    print("Content was shortened.", file=sys.stderr)


def call_einfra(prompt, api_key) -> str:
    i = 0
    while True:
        einfra_messages = []
        for record in prompt:
            einfra_messages.append({
                "role": record["role"],
                "content": [
                    {
                        "type": "text",
                        "text": record["content"].replace("<|message|>", "").replace("<|channel|>", "").replace("<|end|>", "").replace("<|start|>", "")
                    }
                ]
            })


        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "deepseek-r1",
            "messages": einfra_messages,
            "temperature": 0.2,
            "max_tokens": 60000,
        }

        try:
            resp = requests.post("https://chat.ai.e-infra.cz/api/chat/completions", headers=headers, json=payload, timeout=360)
            resp.raise_for_status()
        except requests.exceptions.HTTPError as e:
            try:
                resp_json = resp.json()
                if "Requested token count exceeds the model's maximum context length of" in resp_json["message"]:
                    shorten_prompt(prompt)
                    continue
            except Exception:
                pass
            time.sleep(60)
            i += 1
            print(einfra_messages, file=sys.stderr)
            print(resp.text, file=sys.stderr)
            if i >= 10:
                raise e
            continue
        break
    return resp.json()["choices"][0]["message"]["content"]


def tune_prompt(params: dict[str, str], corpinfo: dict[str, Any]) -> None:
    prompt = json.loads(params["prompt"])
    corpname = params.get("corpname", "__other__")
    api_key_einfra = params.get("api_key_e-infra", "")

    corpus_info = get_corpinfo_prompt_cached(corpname, corpinfo, api_key_einfra)

    system_instructions = (
        "You are an expert assistant for Sketch Engine's Corpus Query Language (CQL).\n"
        "Your job is to read the conversation and translate the user's *latest* request "
        "into a single CQL query.\n"
        "\n"
        "Important CQL reminders:\n"
        "- A query is a sequence of tokens, each inside square brackets: [ ... ].\n"
        "- Use attributes like word, lemma, tag, lc, lempos, structure attributes, etc.\n"
        "- Use regular expressions only when necessary.\n"
        "- Prefer lemma=\"...\" when the user asks for 'all forms' of a word.\n"
        "- Follow corpus-specific tags, annotations, structures and grammatical relations.\n"
        "\n"
        f"Corpus description for corpus '{corpname}':\n"
        f"{corpus_info}\n"
        "\n"
        "Output format requirements (very important):\n"
        "1. Respond with EXACTLY one fenced code block.\n"
        "2. The fence must be in this format:\n"
        "```cql\n"
        "[your CQL query here]\n"
        "```\n"
        "3. Do output any text before the code block. Use this for reasoning.\n"
        "4. Do explain the query, comment on it, or paraphrase the user. Before the code block.\n"
        "5. Do not ask for clarification. Respond directly.\n"
    )

    # Prepend/augment the system message
    if prompt and prompt[0].get("role") == "system":
        prompt[0]["content"] = system_instructions + "\n\n" + prompt[0].get("content", "")
    else:
        prompt.insert(0, {"role": "system", "content": system_instructions})

    params["prompt"] = json.dumps(prompt)


def call(params: dict[str, str]) -> str:
    api_key = params["api_key_e-infra"]
    prompt = json.loads(params["prompt"])

    model_response = call_einfra(prompt, api_key)

    prompt.append({
        "role": "assistant",
        "content": model_response,
    })

    params["prompt"] = json.dumps(prompt)

    try:
        cql = model_response.split("```")[-2].strip().replace("\n", "")
    except Exception:
        cql = ""

    if cql.lower().startswith("cql"):
        cql = cql[3:].strip()
    if cql.startswith(":"):
        cql = cql[1:].strip()
    print(cql, file=sys.stderr)
    return cql


def auto_call(params: dict[str, str]) -> str:
    cql = call(params)

    if len(cql) == 0:
        prompt = json.loads(params["prompt"])
        prompt.append({
            "role": "user",
            "source": "auto_call",
            "source_status": "nocql",
            "content": "I was unable to detect the resulting CQL. Could you provide it in a code block? Like: ```<CQL>```.",
        })
        params["prompt"] = json.dumps(prompt)
        cql = call(params)

    if params["corpname"] != "__other__":
        try:
            import cql_checker
            check_cql = cql_checker.check_cql
        except ModuleNotFoundError:
            def check_cql(corpname: str, cql: str) -> None:
                cql_urlencoded = urllib.parse.quote_plus(cql)
                corpname_urlencoded = urllib.parse.quote_plus(corpname)
                response = requests.get(f"https://app.sketchengine.eu/bonito/run.cgi/check_cql?corpname={corpname_urlencoded}&cql={cql_urlencoded}&format=json", headers={"accept": "application/json", "Authorization": "Bearer " + params["api_key_ske"]}).json()
                if "error" in response:
                    raise Exception(response["error"])

        for _ in range(3):
            error = ""
            try:
                check_cql(params["corpname"], cql)
            except Exception as e:
                error = str(e)
            if len(error) > 0:
                prompt = json.loads(params["prompt"])
                prompt.append({
                    "role": "user",
                    "source": "auto_call",
                    "source_status": "error",
                    "content": f"The generated cql:\n```{cql}```\n is incorrect.\n\nThe error from parser is: {error}. Please fix it and provide a new CQL.",
                })
                params["prompt"] = json.dumps(prompt)
                cql = call(params)
                continue
            break
    return cql
