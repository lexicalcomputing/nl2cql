# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

import sys
import json

ROWS = 0
results = {}

loaded = False

for line in sys.stdin:
    print(repr(line))
    print("----")
    line = line.strip()

    if len(line) == 0:
        continue

    j = json.loads(line.split("\t")[-1])
    if not loaded:
        loaded = True
        for key in j:
            if key == "ERROR":
                continue
            results[key] = 0

    ROWS += 1
    for key in j:
        if key == "ERROR":
            continue
        results[key] += j[key]

for key in results:
    results[key] = results[key] / ROWS * 100
    print(f"{key}: %f" % (results[key], ))

