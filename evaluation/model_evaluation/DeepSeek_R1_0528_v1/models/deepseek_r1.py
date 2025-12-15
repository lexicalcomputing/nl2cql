# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

import models.corpinfo_prompt as corpinfo_prompt
import json
import urllib.parse
import requests
import time
import sys


def shorten_prompt(prompt):
    lens = []
    for i, content in enumerate(prompt):
        if i == 0:
            continue
        if content["role"] == "assistant":
            lens.append(len(content["content"]), i)

    lens.sort()
    prompt.pop(lens[-1][1])
    if lens[-1][1] != 1:
        prompt.pop(lens[-1][1] - 1)

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
                    shorten_prompt()
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



def tune_prompt(params: dict[str, str], corpinfo: dict[str, str]) -> None:
    prompt = json.loads(params["prompt"])
    corpinfo = corpinfo_prompt.get_corpinfo_prompt(params["corpname"], corpinfo)
    tune = r"""Definition of Corpus Query Language (CQL)
    The CQL is a query language used in Sketch Engine for searching grammatical and lexical patterns. CQL sets criteria for positions and tokens, such as tag, word, lemma, lempos, etc.
    Basic syntax is [attribute="value"], for example:
    To find the lemma teapot, use
    CQL:
    ```
    [lemma="teapot"]
    ```
    Each token must be inside its own pair of square brackets. To search for the phrase refill the teapot, use
    CQL:
    ```
    [lemma="refill"][lemma="the"][lemma="teapot"]
    ```
    More examples:
    find examples of went -> CQL:
    ```
    [word="went"]
    ```
    find examples of all forms of go -> CQL:
    ```
    [lemma="go"]
    ```
    find examples of all words tagged with the tag NP -> CQL:
    ```
    [tag="NP"]
    ```

    Regular expressions can be used with values in CQL. A complete set of Regular expressions is supported, and complex criteria can be used, for example:
    words starting with confus- -> CQL:
    ```
    [lemma="confus.*"]
    ```
    words ending with -ious -> CQL:
    ```
    [lemma=".*ious"]
    ```
    three-letter words starting b- and ending -g -> CQL:
    ```
    [lemma="b.g"]
    ```
    Be aware that when searching for any of the characters [][.*+{}?()|\\"$^] literally, they must be escaped using a backslash in any context where you may used regular expressions.

    Square brackets [ ] stand for "any token". Curly brackets { } are used for repetition of the preceding token, for example:
    find examples of ‘refill’ and ‘kettle’ with one word in between -> CQL:
    ```
    [lemma="refill"] [ ] [lemma="kettle"]
    ```
    examples of ‘have’ and ‘opinion’ with 2 to 4 words in between -> CQL:
    ```
    [lemma="have"] [ ]{2,4}[lemma="opinion"]
    ```
    find examples of "drink" and "water" with exactly two adjectives between them -> CQL:
    ```
    [lemma="drink"] [tag="J.*"]{2}[lemma="water"]
    ```

    A token can be made optional by placing a question mark ? after the square bracket. For example:
    Find examples of ‘drive my car’ or ‘drive my own car’ -> CQL:
    ```
    [lemma="drive"] [lc="my"] [lc="own"]? [lemma="car"]
    ```
    alternative solution without using ? -> CQL:
    ```
    [lemma="drive"][lc="my"][lc="own"]{0,1} [lemma="car"]
    ```

    These comparison operators are supported:
    equal =
    less than or equal to <=
    more than or equal to >=
    not equal !=
    not less than or equal to !<=
    not more than or equal to !>=
    equal (no regex) ==
    not equal (no regex) !==
    The alphabetical parts of the value are compared lexicographically (‘in the dictionary order’) and numerical parts numerically. This is useful with structure attributes, where >="AB2010CD" will include values such as "BB0000CD", "AB2011CD" or "AB2010CE". Example:
    all one-letter words -> CQL:
    ```
    [word="."]
    ```
    all full stops -> CQL:
    ```
    [word=="."]
    ```

    One token can have more conditions. They must all appear inside the same pair of square brackets, and Boolean operators must be used between them.
    & (ampersand) = AND
    | (pipe) = OR
    ! (exclamation mark) = NOT
    For example:
    Find all forms of the word ‘test’ which is a noun -> CQL:
    ```
    [ lemma="test" & tag="N.*" ]
    ```
    finds word ‘test’ which is NOT a verb -> CQL:
    ```
    [word="test" & tag!="V.*"]
    ```
    finds the word round tagged as a noun or verb -> CQL:
    ```
    [ word="round" & ( tag="N.*" | tag="V.*" ) ]
    ```
    finds word ‘test’ which is NOT a verb -> CQL:
    ```
    [word="test" & !tag="V.*"]
    ```

    | (pipe) = OR - means one token or another token, i.e., the token to the right or left of the pipe.
    This use of the pipe (|) should only be limited to cases with no other solution because it consumes the search time. In most cases, it can be replaced by a pipe used inside the token, which is faster. See examples below.
    "big dog" or "wolf" -> CQL:
    ```
    ([lemma="big"][lemma="dog"]) | [lemma="wolf"]
    ```

    Structures refer to sentences, paragraphs, documents, or any other parts or sections into which a corpus might be divided. Another way of saying this is that certain parts of a corpus can be labelled, e.g., direct speech might be labelled using structures to make it possible to limit the search to only direct speech. Structures may or may not have values. Values are used to categorize instances of the same structure.
    Structures can be referred to in three ways:
    The beginning: <s> <p> <doc> etc.
    The end: </s> </p> </doc> etc.
    The whole structure: <s/> <p/> <doc/> etc.
    For example:
    Find all documents written in informal style that start with the word Rebecca -> CQL:
    ```
    <doc style="informal">[lemma="Rebecca"]
    ```
    find all documents whose ID is 2011 and they start with a noun followed by a verb at a distance of up to 5 words -> CQL:
    ```
    <doc id="2011"> [tag="N.*"] []{0,5} [tag="V.*"]
    ```
    Written documents whose ID is 2011 and they start with a noun followed by a verb at a distance of up to 5 words -> CQL:
    ```
    <doc id="2011" & type="written"> [tag="N.*"] []{0,5} [tag="V.*"]
    ```
    find all verbs written in informal style -> CQL:
    ```
    [tag="V.*"]  within <doc style="informal" />
    ```

    The "containing" and "within" CQL operators are used to restrict the search only to a certain structure, e.g., to search inside:
    Corpus structure, e.g., sentence, paragraph, document, etc.
    Grammatical or lexical structure, e.g., noun phrase.

    Use within to ensure the search result appears within the structure you want, in this case, within the same sentence, paragraph, document, or any other structure found in the corpus:
    CQL:
    ```
    [word="dog"] []{0,5} [word="runs"] within < s/>
    ```
    The structure after "within" can be another CQL code defining a grammatical or lexical structure:
    CQL:
    ```
    [tag="N.*"] within [tag="VB.*"] []{0,5} [tag="VB.*"]
    ```
    Multiple within operators can be nested if necessary:
    CQL:
    ```
    [tag="N.*"] within ([tag="VB.*"] []{0,5} [tag="VB.*"] within < s/>)
    ```
    Use within to search a parallel corpus using this syntax:
    within :
    For example, with the English Europarl open, you can use this CQL to query the German Europarl. It will find all segments where the English corpus contains car and the aligned German segment contains Auto. In most cases, these will be segments where car was translated as Auto:
    CQL:
    ```
    [word="car"] within europarl5_de: [word="Auto"]
    ```

    Use containing to find the whole structure and to display the whole structure as the result (KWIC).
    This will find all paragraphs containing an acronym, i.e. a word consisting of 3 or more upper-case characters:
    CQL:
    ```
    <p/> containing [word="[A-Z]{3,}"]
    ```
    This query searches for noun phrases (sequences of up to 5 adjectives followed by a noun) that contain the adjective international:
    ```
    [tag="J.*"]{1,5} [tag="N.*"] containing [word="international"]
    ```

    Use ! for negation:
    !within = not within
    !containing = not containing

    This CQL will find all nouns that appear outside the <nphr> structure, i.e., outside noun phrases. The CQL will only work in corpora where the <nphr> structure exists:
    CQL: ```
    [tag="N.*"]   !within   <nphr/>
    ```
    This CQL will find all sentences that do not contain any word starting with a capital letter:
    CQL:
    ```
    <s/>   !containing   [word="[A-Z][A-Za-z]*"]
    ```

    Simultaneously searching the left and right context is only possible with meet and union operators. This is useful when a user wants to search for a token that is around or in the area of some other token.
    Use meet to set the left and right context. This will find all nouns that have the verb to be 3 tokens to the left or 3 tokens to the right:
    CQL:
    ```
    (meet [tag = "N.*"] [tag = "VB.*"] -3 3)
    ```
    Use the operator union to collect the results of two meet queries and display them in one concordance.
    This CQL will, find all nouns with the verb to be at a distance of 3 tokens to the left or right, then find all adjectives with the verb to be at a distance of 2 tokens to the left or right, combine the nouns from the first query and adjectives from the second query and display them together in one concordance, the nouns and adjectives will be highlighted in the centre as KWIC:
    CQL:
    ```
    (union (meet [tag="N.*"] [tag="VB.*"] -3 3) (meet [tag="A.*"] [tag="VB.*"] -2 2))
    ```
    This combines instances of nouns preceded by competent with adjectives followed by competence:
    CQL:
    ```
    (union(meet [tag="N.*"] [lemma="competent"] -2 -1)(meet [tag="J.*"] [lemma="competence"]  1 2))
    ```
    Note that each meet and union has to be inside its own pair of brackets. Operators meet, and a union cannot be used with operators within and containing.

    CQL also supports word sketch. Word sketches provide collocations for a word. The syntax is as follows:
    CQL:
    ```
    [ws(headword, relation, collocation)]
    ```
    The relation is the name of the relation. You can often guess the name by using a regular expression like this:
    CQL:
    ```
    [ws(headword, ".*subject.*", collocation)]
    ```
    For the exact name of the relation, the "%w" must be exchanged for \"%w\" as the quotes need to be backslashed in CQL. For example, the Word Sketch relation modifiers of "book" can be written as a CQL query:
    CQL:
    ```
    [ws("book-n", "modifiers of \"%w\"", ".*")]
    ```
    Remember that Word Sketches are generated from lempos, so using a hyphen and the shortened PoS tag is necessary. For example, to generate a concordance with test (as a noun) being the object of conduct (as a verb), use this:
    CQL:
    ```
    [ws("test-n",".*object.*","conduct-v")]
    ```
    In the resulting concordance, the headword is taken for a KWIC, and the collocations are used as a filter. It is possible to specify the headword by using the regular expression AND inside the square brackets. For example, to search for all relations of lempos "book-n" where the word appears in the plural form, you can use a CQL query:
    CQL:
    ```
    [ws("book-n", ".*", ".*") & tag="NNS"]
    ```
    The prepositional phrases can be searched by the following syntax:
    CQL:
    ```
    [ws("headword", "\.\.\. [^ /]+ \"%w\"", ".*") | ws("headword", "\"%w\" [^ /]+ \.\.\.", ".*")]
    ```
    In case only specific prepositions should be displayed, it is possible to insert them instead of [^ /]. This example will find concordance lines with the headword ‘test’ as a noun and prepositions of, in, or at:
    CQL:
    ```
    [ws("test-n", "\.\.\. (of|in|at) \"%w\"", ".*") | ws("test-n", "\"%w\" (of|in|at) \.\.\.", ".*")]
    ```
    The Word Sketch CQL can be combined with other CQL markers. To generate a concordance where the headword test is modified by blood and followed or preceded by the lemma be, use this:
    CQL:
    ```
    (meet [ws("test-n",".*modifiers of.*","blood-n")] [lemma="be"] -1 1)
    ```

    Thesaurus is also supported in CQL. Use the tilde ~ to generate a thesaurus (words with similar context, synonyms, antonyms) for the word and include the top N thesaurus items into the query. For example, to find the verb chop followed by vegetables, use this (or replace carrot with any other vegetable):
    CQL:
    ```
    [lemma="chop"] []{0,3} ~"carrot-n"
    ```
    To set the number of thesaurus items manually, use:
    CQL:
    ```
    ~15"carrot-n"
    ```
    CQL:
    ```
    [lemma="chop"] []{0,3} ~15"carrot-n"
    ```
    Thesaurus may be used with meet keyword, for example, to find all metals around the lemma corrosion:
    CQL:
    ```
    (meet ~"metal-n" [lemma="corrosion"] -5 5)
    ```

""" + corpinfo["attributes"] + corpinfo["annotations"] + corpinfo["annotations_full"] + corpinfo["lempos_suffixes"] + corpinfo["structures_and_attributes"] + corpinfo["gramrels"] + corpinfo["language"] + """
Analyze if you need to use provided annotations, attributes, structures and more, reason as much as possible. Consider translating given words, when input language differs from corpus language. Make great effort to satisfy whole history of the conversation and requests to completely change the topic. With this information answer following query: """

    prompt[0]["content"] = tune + prompt[0]["content"]
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
