# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

import sys
import json
import os
import requests
import urllib.parse
import models.Qwen3_Coder_30B_A3B_Instruct_IQ4_NL as model

if __name__ == "__main__":
    if os.path.exists("corpinfo_cache.json"):
        with open("corpinfo_cache.json") as file:
            model._CORPINFO_CACHE = json.load(file)
    for i, line_gold in enumerate(sys.stdin):
        print(repr(line_gold), file=sys.stderr)
        if line_gold == "\n":
            continue
        print(f"On line {i + 1}", file=sys.stderr)
        line_gold = line_gold.strip()
        query, corpname, cql_gold = line_gold.split("\t", 2)

        params = {
            "api_key_e-infra": os.environ.get("API_KEY_EINFRA"),
            "api_key_ske": os.environ.get("SKE_API_KEY")
        }

        params["corpname"] = corpname

        params["prompt"] = json.dumps([{
            "role": "user",
            "content": query
        }])

        HEADERS = {"accept": "application/json", "Authorization": "Bearer " + os.environ.get("SKE_API_KEY")}
        corpus_url_component = urllib.parse.quote_plus(corpname)
        response = requests.get(f"https://api.sketchengine.eu/search/corp_info?corpname={corpus_url_component}&struct_attr_stats=1&subcorpora=1&gramrels=1&registry=1&format=json", headers=HEADERS).json()

        corpinfo = response

        model.tune_prompt(params, corpinfo)
        translation = model.auto_call(params)

        print("\t".join([query, corpname, cql_gold, translation]))
    with open("corpinfo_cache.json", "w") as file:
        json.dump(model._CORPINFO_CACHE, file)
