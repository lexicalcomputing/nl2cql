# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

from typing import Any
import json
import requests
import time
import sys


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
            "temperature": 1,
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

    # What is the Corpus Query Language?
    instructions = "**Corpus Query Language (CQL)** is a specialized syntax for searching and analyzing large collections of text (corpora). It combines **regular expressions** with tools to target linguistic annotations (e.g., lemmas, part-of-speech tags, syntactic features), enabling precise, complex queries in corpus linguistics or NLP.  \n\n### Key Features:\n1. **Annotation-Aware Search**  \n   Queries can match both surface text (*tokens*) and metadata (e.g., `[lemma=\"run\"]` finds \"run\", \"ran\", \"running\").  \n2. **Regular Expression Support**  \n   Wildcards (`.*`), character classes (`[aeiou]`), and quantifiers (`\"the\"+` for \"the\", \"thethe\", etc.).  \n3. **Structural Constraints**  \n   Match spans (e.g., `[pos=\"NOUN\"] [pos=\"NOUN\"]` for compound nouns) or depend on syntax trees.  \n\n### Syntax Examples:\n- `[word=\"bank\" & pos=\"NOUN\"]`: Find *bank* only as a noun.  \n- `\"run\"`: Find the exact word \"run\".  \n- `[lemma=\"go\"]`: Find all forms (*go*, *went*, *gone*).  \n- `[pos=\"ADJ\"] [pos=\"NOUN\"]`: Find adjective-noun pairs (e.g., *blue sky*).  \n\n### Practical Use Case:  \n> Find all passive constructions using the lemma \"see\":  \n> ```cql\n> [lemma=\"be\"] [tag=\"V.*\"][lemma=\"see\" & tag=\"VBN\"]  \n> ```  \n> Matches: \"*was seen*\", \"*is seen*\", etc.  \n\n### Tools Supporting CQL:  \n- **CQP** (Corpus Query Processor)  \n- **Sketch Engine**  \n- **NoSketch Engine**  \n- **ANNIS**  \n\n**Note:** CQL dialects vary slightly between tools. For instance, **CQP syntax** (an early implementation) inspired modern CQL variants used today. CQL is essential for corpus-based research, lexicography, and linguistic analysis."
    

    prompt[0]["content"] = "Answer in a codeblock. I need a CQL for: " + prompt[0]["content"]
    prompt.insert(0, {"role": "user", "content": "What is a Corpus Query Language?"})
    prompt.insert(1, {"role": "assistant", "content": instructions})
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
    return cql
