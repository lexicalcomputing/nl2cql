# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

grammar = """
root ::= think text block

think ::= "<think>" beforethink "</think>"

beforethink ::= (
      [^<]
    | "<" [^/]
    | "</" [^t]
    | "</t" [^h]
    | "</th" [^i]
    | "</thi" [^n]
    | "</thin" [^k]
    | "</think" [^>]
)*

text ::= (
    [^`]
    | "`" [^`]
    | "``" [^`]
)*

block ::= "```cql\\n" cql "\\n```"

cql ::= within (space "&" space globalconsts)? (space ("containing"|"within" space parallelcorpora?) space cql)* 

globalconsts ::= (
    globalconst
    | globalconst space [&|] globalconsts
    | space "(" space globalconsts space ")" space
)

globalconst ::= (
    space [1-9][0-9]* "." tokenA space globalO space [1-9][0-9]* "." tokenA space
    | space "f" space "(" space [1-9][0-9]* "." tokenA space ")" space globalOO space [0-9]+ space
)

globalO ::= (
    "="
    | "!="
)

globalOO ::= (
    globalO
    | "<"
    | ">"
)

space ::= (" ")*

within ::= (
    (space keyword space)+
    | "(" space within space ")" (space repetition space)?
    | space keyword+ (("|" | ("!")? "containing" | ("!")? "within") space keyword+ space)+
    | space keyword+ ("|" | ("!")? "containing" | ("!")? "within") space [0-9]+ space
    | "(" within ")" space "|" space "(" within ")"
    | "(" within ")" ("|" | ("!")? "containing" | ("!")? "within") space [0-9]+ space
)

keyword ::= ( 
    space 
(
    token space [&|]? space keyword?
    | structure space [&|]? space keyword?
    | thesaurus space [&|]? space keyword?
    | "(" keyword ")" (space repetition space)? space [&|]? space keyword?
    | "\\"" regex "\\"" space repetition? space [&|]? space keyword?
    | "(" keyword+ (space "|" space keyword+ )? ")" space [&|]? space keyword?
    | meet space [&|]? space keyword?
    | union space [&|]? space keyword?
    | space "(" space within space ")" space repetition?
)
    space
)

thesaurus ::= "!"? space "~" [0-9]* "\\"" regex "-" [a-z] "\\""

repetition ::= (
space
(
    "?"
    | "*"
    | "+"
    | "{" space [0-9]+ space "," space [0-9]* space "}"
    | "{" space "," space [0-9]+ space "}"
    | "{" space [0-9]+ space"}"
)
space
)

globalmark ::= space [1-9][0-9]* space ":" space

token ::= globalmark? "[" space (tokenconstraints)? space "]" repetition?

tokenconstraints ::= (
    space
(
    tokenconstraint
    | "(" tokenconstraints ")"
    | "(" tokenconstraints ")" space [&|] space tokenconstraints
    | tokenconstraint space [&|] space tokenconstraints
)
    space
)

tokenconstraint ::= (
space
(
    ("!" space)? tokenA space tokenO space tokenV
    | wordsketch
    | thesaurus
    | term
    | range
)
space
)

tokenA ::= %%TOKEN_ATTRIBUTES%%

tokenO ::= "=" | "==" | "!=" | "!==" | ">=" | "<="

tokenV ::= "\\"" regex "\\""

#regex ::= ([^"] | "\\\"")*
regex ::= ([^"] | "\\\\\\"")*

structure ::= %%STRUCTURES%%
%%STRUCTURE_ENTRIES%%

structureO ::= tokenO

structureV ::= tokenV

term ::= space "term(" space "\\"" regex "\\"" space ")" space

wordsketch ::= space "ws(" space "\\"" regex "\\"" space "," space "\\"" regex "\\"" space "," space "\\"" regex "\\"" space ")" space

range ::= "#" [0-9]+ ("-" [0-9]+)?

meet ::= "(meet" space keyword space keyword space ("-"? [0-9]+ " " space "-"? [0-9]+)? space ")"

union ::= "(union" space meet space meet space ")"

parallelcorpora ::= [^ :]* ": "
"""

structures_grammar = """
structureentery%%STRUCT_NAME%% ::= space ("!")? space "<" space ("/")? space "%%RAW_NAME%%" space structureconstraints%%STRUCT_NAME%%? space ("/")? space ">" space

structureconstraints%%STRUCT_NAME%% ::= (
space
(
    structureconstraint%%STRUCT_NAME%%
    | "(" structureconstraints%%STRUCT_NAME%% ")"
    | "(" structureconstraints%%STRUCT_NAME%% ")" space [&|] structureconstraints%%STRUCT_NAME%%
    | structureconstraint%%STRUCT_NAME%% space ([&|] space structureconstraint%%STRUCT_NAME%%)+

)
space
)

structureconstraint%%STRUCT_NAME%% ::= structureA%%STRUCT_NAME%% space structureO space structureV

structureA%%STRUCT_NAME%% ::= %%STRUCTURE_ATTRS%%
"""

import sys
import os
import requests
import urllib.parse

def get_grammar(grammar, token_attributes = ("word", "tag", "lemma", "lc", "lempos_lc", "lempos", "lemma_lc"), structures = (("s", ("audio", )), ("g", ()), ("p", ()), ("u", ()), ("sp", ("who", )), ("vocal", ("desc", )), ("bncdoc", ("alltyp", "wridom", "sdesex", "sdeage", "year", "sporeg", "wriase", "writas", "alltim", "info", "alltim", "genre", "scgdom", "sporeg")))):
    grammar = grammar.replace("%%TOKEN_ATTRIBUTES%%", "|".join([f"\"{key}\"" for key in token_attributes]))
    structgrammar = []
    structures_list = []
    for s in structures:
        sattributes = "|".join(f"\"{key}\"" for key in s[1])
        if len(sattributes) == 0:
            sattributes = "()"
        sclean = s[0].replace("_", "yxzh")
        for i in range(10):
            sclean = sclean.replace(str(i), chr(ord('a') + i)*4)
        structures_list.append(sclean)
        structgrammar.append(structures_grammar.replace("%%STRUCT_NAME%%", sclean).replace("%%RAW_NAME%%", s[0]).replace("%%STRUCTURE_ATTRS%%", sattributes))
    grammar = grammar.replace("%%STRUCTURES%%", " | ".join([f"structureentery{key}" for key in structures_list]))
    grammar = grammar.replace("%%STRUCTURE_ENTRIES%%", "".join(structgrammar))
    return grammar

def get_corpinfo(corpname: str, api_key: str) -> dict:
    attr = {}
    HEADERS = {"accept": "application/json", "Authorization": "Bearer " + api_key}
    corpus_url_component = urllib.parse.quote_plus(corpname)
    response_raw = requests.get(f"https://api.sketchengine.eu/search/corp_info?corpname={corpus_url_component}&struct_attr_stats=1&subcorpora=1&gramrels=1&registry=1&format=json", headers=HEADERS)
    response = response_raw.json()
    attr["token_attr"] = []
    for a in response["attributes"]:
        attr["token_attr"].append(a["name"])
    attr["structures"] = []
    for s in response["structures"]:
        sa = []
        for a in s["attributes"]:
            sa.append(a["name"])
        attr["structures"].append([s["name"], sa])
    return attr

if __name__ == "__main__":
    corpname = sys.argv[1]
    api_key = os.environ["SKE_API_KEY"]
    attr = get_corpinfo(corpname, api_key)
    print(get_grammar(grammar, token_attributes=attr["token_attr"], structures=attr["structures"]))
