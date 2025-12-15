# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

from typing import Dict, Tuple, List
import urllib.parse
import requests
import json
import sys
import re
from nltk.translate.bleu_score import sentence_bleu


RE_SAPCES = re.compile(r" +")


cql_tokenizer_token2id = {}


ON_ERROR = {
    "n_grams_1": 0,
    "n_grams_2": 0,
    "n_grams_3": 0,
    "n_grams_4": 0,
    "n_grams_5": 0,
    "n_grams_6": 0,
    "bleu": 0,
    "precision": 0,
    "recall": 0,
    "f1": 0,
    "maximal intersection over union": 0,
    "maximal intersection over union +-1": 0,
    "maximal intersection over union +-2": 0,
    "sentence_precision": 0,
    "sentence_recall": 0,
}


def cql_tokenizer(cql: str, pad: int = 4) -> List[int]:
    global cql_tokenizer_token2id

    cql = cql.replace(" ", "")
    cql = cql.replace("\n", "")
    cql = cql.replace("[", " [ ")
    cql = cql.replace("]", " ] ")
    cql = cql.replace("{", " { ")
    cql = cql.replace("}", " } ")
    cql = cql.replace("(", " ( ")
    cql = cql.replace(")", " ) ")
    cql = cql.replace(",", " , ")
    cql = cql.replace("=", " = ")
    cql = cql.replace("!", " ! ")
    cql = cql.replace("~", " ~ ")
    cql = cql.replace("|", " | ")
    cql = cql.replace("&", " & ")
    cql = cql.replace("+", " + ")
    cql = cql.replace("*", " * ")
    cql = cql.replace("?", " ? ")
    cql = cql.replace("\"", " \" ")
    cql = cql.replace("<", " < ")
    cql = cql.replace(">", " > ")
    cql = cql.replace(".", " . ")
    cql = cql.replace("^", " ^ ")
    cql = cql.replace("$", " $ ")
    cql = cql.replace("@", " @ ")
    cql = cql.replace("'", " ' ")
    cql = cql.replace("within", " within ")
    cql = cql.replace("containing", " containing ")
    cql = cql.replace("meet", " meet ")
    cql = RE_SAPCES.sub(" ", cql).strip()

    cql_ids = []
    for token in cql.split(" "):
        if token not in cql_tokenizer_token2id:
            cql_tokenizer_token2id[token] = len(cql_tokenizer_token2id)
        cql_ids.append(cql_tokenizer_token2id[token])

    while len(cql_ids) < pad:
        cql_ids.append(-1)
    return cql_ids


def n_gram_precision(n, values, target):
    match = 0
    visited = 0
    for i in range(len(values) - n + 1):
        visited += 1
        for p in range(len(target) - n + 1):
            if values[i:i + n] == target[p:p + n]:
                match += 1
                break
    if visited == 0:
        return 0
    return match / visited


def IoU(a: Tuple[int, int], b: Tuple[int, int]) -> float:
    if a[0] > b[0]:
        a, b = b, a
    if a[1] < b[0]:
        return 0

    max_v = a[1] if a[1] > b[1] else b[1]
    min_v = a[0]

    if a[1] > b[1]:
        return (b[1] - b[0] + 1) / (max_v - min_v + 1)
    return (a[1] - b[0] + 1) / (max_v - min_v + 1)


def get_sentence_hits(corpname: str, pos_list, SKETCH_ENGINE_API_KEY: str = "", limit: int = 1000):
    if len(pos_list) == 0:
        return
    HEADERS = {"accept": "application/json", "Authorization": "Bearer " + SKETCH_ENGINE_API_KEY}
    pos_list_str = [str(x) for x in pos_list]
    cql = "<s/> containing [#" + "|#".join(pos_list_str) + "]"
    json_param = json.dumps(
        {
            "concordance_query": [
                {
                    "queryselector": "cqlrow",
                    "cql": cql,
                    "default_attr": "word"
                }
            ]
        }
    )
    resp_json = requests.post(f"https://app.sketchengine.eu/bonito/run.cgi/concordance?corpname={urllib.parse.quote_plus(corpname)}&default_attr=word&attrs=pos&attr_allpos=all&viewmode=sen&cup_hl=q&structs=s,g&fromp=1&pagesize={str(limit)}&kwicleftctx=0&kwicrightctx=0", headers=HEADERS, data={"json": json_param}).json()
    for hit in resp_json["Lines"]:
        yield hit["toknum"]


def cqlcmp(gold_cql: str, cql: str, corpname: str, limit: int = 1000, SKETCH_ENGINE_API_KEY: str = "", verbose: bool = False) -> Dict[str, float]:
    if gold_cql.strip() == cql.strip():
        return {
            "n_grams_1": 1,
            "n_grams_2": 1,
            "n_grams_3": 1,
            "n_grams_4": 1,
            "n_grams_5": 1,
            "n_grams_6": 1,
            "bleu": 1,
            "precision": 1,
            "recall": 1,
            "f1": 1,
            "maximal intersection over union": 1,
            "maximal intersection over union +-1": 1,
            "maximal intersection over union +-2": 1,
            "sentence_precision": 1,
            "sentence_recall": 1,
        }

    HEADERS = {"accept": "application/json", "Authorization": "Bearer " + SKETCH_ENGINE_API_KEY}
    json_gold_param = urllib.parse.quote_plus(json.dumps(
        {
            "concordance_query": [
                {
                    "queryselector": "cqlrow",
                    "cql": gold_cql,
                    "default_attr": "word"
                }
            ]
        }
    ))
    if verbose:
        print(f"CQL: {gold_cql}", file=sys.stderr)
    response_gold_json = requests.get(f"https://app.sketchengine.eu/bonito/run.cgi/concordance?corpname={urllib.parse.quote_plus(corpname)}&default_attr=word&attrs=pos&attr_allpos=all&viewmode=sen&cup_hl=q&structs=s,g&fromp=1&pagesize={str(limit)}&kwicleftctx=0&kwicrightctx=0&json={json_gold_param}", headers=HEADERS).json()

    json_param = urllib.parse.quote_plus(json.dumps(
        {
            "concordance_query": [
                {
                    "queryselector": "cqlrow",
                    "cql": cql,
                    "default_attr": "word"
                }
            ]
        }
    ))
    if verbose:
        print(f"CQL: {cql}", file=sys.stderr)
    response_json = requests.get(f"https://app.sketchengine.eu/bonito/run.cgi/concordance?corpname={urllib.parse.quote_plus(corpname)}&default_attr=word&attrs=pos&attr_allpos=all&viewmode=sen&cup_hl=q&structs=s,g&fromp=1&pagesize={str(limit)}&kwicleftctx=0&kwicrightctx=0&json={json_param}", headers=HEADERS).json()

    cql_ids = cql_tokenizer(cql)
    gold_cql_ids = cql_tokenizer(gold_cql)

    if "error" in response_json:
        if not (response_json["error"].startswith("syntax error, ") or response_json["error"].startswith("unexpected character ") or response_json["error"].startswith("regexopt: regex optimization parsing error")):
            print(response_json, file=sys.stderr)
        return {
            "n_grams_1": n_gram_precision(1, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "n_grams_2": n_gram_precision(2, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "n_grams_3": n_gram_precision(3, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "n_grams_4": n_gram_precision(4, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "n_grams_5": n_gram_precision(5, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "n_grams_6": n_gram_precision(6, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
            "bleu": sentence_bleu([gold_cql_ids], cql_ids, weights=(0.25, 0.25, 0.25, 0.25)),
            "precision": 0,
            "recall": 0,
            "f1": 0,
            "maximal intersection over union": 0,
            "maximal intersection over union +-1": 0,
            "maximal intersection over union +-2": 0,
            "sentence_precision": 0,
            "sentence_recall": 0,
        }

    gold_dict = {}
    for hit in response_gold_json["Lines"]:
        if hit["toknum"] in gold_dict:
            gold_dict[hit["toknum"]].append(hit["hitlen"])
            continue
        gold_dict[hit["toknum"]] = [hit["hitlen"]]

    sentence_hits_gold = set(get_sentence_hits(corpname, list(gold_dict.keys()), SKETCH_ENGINE_API_KEY, limit))
    token_pos = []
    for hit in response_json["Lines"]:
        token_pos.append(hit["toknum"])
    sentence_hits = set(get_sentence_hits(corpname, token_pos, SKETCH_ENGINE_API_KEY, limit))

    sentence_hit = 0
    for hit in sentence_hits:
        if hit in sentence_hits_gold:
            sentence_hit += 1
    sentence_precision = sentence_hit / len(sentence_hits) if len(sentence_hits) > 0 else 0
    sentence_recall = sentence_hit / len(sentence_hits_gold) if len(sentence_hits_gold) > 0 else 0

    hit_counter = 0
    miss_counter = 0
    for hit in response_json["Lines"]:
        if hit["toknum"] in gold_dict and hit["hitlen"] in gold_dict[hit["toknum"]]:
            hit_counter += 1
        else:
            miss_counter += 1
    remains_counter = len(response_gold_json["Lines"]) - hit_counter
    precision = hit_counter / (hit_counter + miss_counter) if hit_counter + miss_counter > 0 else 0
    recall = hit_counter / (hit_counter + remains_counter) if hit_counter + remains_counter > 0 else 0
    f1 = (2 * hit_counter) / (2 * hit_counter + remains_counter + miss_counter) if 2 * hit_counter + remains_counter + miss_counter > 0 else 0

    max_iou_list = []
    for hit in response_json["Lines"]:
        max_iou = 0
        for gold in gold_dict:
            for i in gold_dict[gold]:
                iou = IoU((hit["toknum"], hit["toknum"] + hit["hitlen"] - 1), (gold, gold + i - 1))
                if iou > max_iou:
                    max_iou = iou
        max_iou_list.append(max_iou)

    max_iou_list_1 = []
    for hit in response_json["Lines"]:
        max_iou = 0
        for gold in gold_dict:
            for i in gold_dict[gold]:
                iou = IoU((hit["toknum"] - 1, hit["toknum"] + hit["hitlen"] - 1 + 1), (gold - 1, gold + i - 1 + 1))
                if iou > max_iou:
                    max_iou = iou
        max_iou_list_1.append(max_iou)

    max_iou_list_2 = []
    for hit in response_json["Lines"]:
        max_iou = 0
        for gold in gold_dict:
            for i in gold_dict[gold]:
                iou = IoU((hit["toknum"] - 2, hit["toknum"] + hit["hitlen"] - 1 + 2), (gold - 2, gold + i - 1 + 2))
                if iou > max_iou:
                    max_iou = iou
        max_iou_list_2.append(max_iou)

    return {
        "n_grams_1": n_gram_precision(1, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "n_grams_2": n_gram_precision(2, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "n_grams_3": n_gram_precision(3, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "n_grams_4": n_gram_precision(4, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "n_grams_5": n_gram_precision(5, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "n_grams_6": n_gram_precision(6, cql_ids, gold_cql_ids) if cql != gold_cql else 1,
        "bleu": sentence_bleu([gold_cql_ids], cql_ids, weights=(0.25, 0.25, 0.25, 0.25)),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "maximal intersection over union": sum(max_iou_list) / len(max_iou_list) if len(max_iou_list) > 0 else 0,
        "maximal intersection over union +-1": sum(max_iou_list_1) / len(max_iou_list_1) if len(max_iou_list_1) > 0 else 0,
        "maximal intersection over union +-2": sum(max_iou_list_2) / len(max_iou_list_2) if len(max_iou_list_2) > 0 else 0,
        "sentence_precision": sentence_precision,
        "sentence_recall": sentence_recall,
    }


if __name__ == "__main__":
    import config
    model_name = sys.argv[1]
    tests = sys.argv[2:]

    results = []

    for test in tests:
        with open(test, "r") as gold_file:
            with open(test + "." + model_name, "r") as model_cqls:
                for line in gold_file:
                    line = line.strip()

                    query, corpname, cql_gold = line.split("\t", 2)

                    cql = model_cqls.readline().strip()

                    results.append(cqlcmp(cql_gold, cql, corpname, 1000, config.SKETCH_ENGINE_API_KEY, verbose=True))
                    print(results[-1])

    average = {}
    for r in results:
        for k in r:
            average[k] = average.get(k, 0) + r[k]
    for k in average:
        average[k] /= len(results)
    print(average)
