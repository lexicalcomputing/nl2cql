
#!/bin/bash

INFILE=$1
IN_PATH=../../datasets_gold/${INFILE}/nl.tsv
OUT_PATH=results/nl_${INFILE}_cql.tsv
ERR_PATH=results/nl_${INFILE}_cql.err

source ./venv/bin/activate

line_count() {
    local path=$1
    if [ -f "$path" ]; then
        wc -l < "$path"
    else
        echo 0
    fi
}

while true; do
    in_lines=$(line_count "$IN_PATH")
    out_lines=$(line_count "$OUT_PATH")

    if [ "$out_lines" -ge "$in_lines" ]; then
        break
    fi

    remaining=$((in_lines - out_lines))
    tail -n "$remaining" "$IN_PATH" | python run_model.py >> "$OUT_PATH" 2>> "$ERR_PATH"
done
