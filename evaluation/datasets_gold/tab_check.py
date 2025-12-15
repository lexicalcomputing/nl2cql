# nl2cql - translation of natural language queries to Corpus Query Language
# Copyright 2025 Ota Mikušek
# This program is licensed under GNU Lesser General Public License

import sys

lines = 0
errors = 0

for filename in sys.argv[1:]:
    print(f"File {filename}:")
    with open(filename, "r") as file:
        for i, line in enumerate(file):
            lines += 1
            if line.count("\t") != 3:
                errors += 1
                print(f"Error on line {i+1}: {(line, line.count("\t"))}")
                continue

            line = line.strip()
            line_splited = line.split("\t")
            if not line_splited[1].startswith("preloaded/"):
                print(f"Error on line {i+1}: Invalid corpus name.")

print(f"{lines-errors} valid lines found")
print(f"{errors} lines with error")
