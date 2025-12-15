.PHONY: run_model cqlcmp

venv:
	python -m venv venv
	. ./venv/bin/activate ; pip install nltk requests html2text

results/nl_czech_cql.tsv: ../../datasets_gold/czech/nl.tsv venv
	mkdir -p results
	. ./venv/bin/activate ; cat ../../datasets_gold/czech/nl.tsv | python run_model.py > results/nl_czech_cql.tsv 2> results/nl_czech_cql.err

results/nl_english_cql.tsv: ../../datasets_gold/english/nl.tsv venv
	mkdir -p results
	. ./venv/bin/activate ; cat ../../datasets_gold/english/nl.tsv | python run_model.py > results/nl_english_cql.tsv 2> results/nl_english_cql.err

results/nl_french_cql.tsv: ../../datasets_gold/french/nl.tsv venv
	mkdir -p results
	. ./venv/bin/activate ; cat ../../datasets_gold/french/nl.tsv | python run_model.py > results/nl_french_cql.tsv 2> results/nl_french_cql.err

run_model: results/nl_czech_cql.tsv results/nl_english_cql.tsv results/nl_french_cql.tsv

results/nl_czech_cql_eval.tsv: results/nl_czech_cql.tsv
	. ./venv/bin/activate ; cat results/nl_czech_cql.tsv | python cqlcmp.py > results/nl_czech_cql_eval.tsv 2> results/nl_czech_cql_eval.err

results/nl_english_cql_eval.tsv: results/nl_english_cql.tsv
	. ./venv/bin/activate ; cat results/nl_english_cql.tsv | python cqlcmp.py > results/nl_english_cql_eval.tsv 2> results/nl_english_cql_eval.err

results/nl_french_cql_eval.tsv: results/nl_french_cql.tsv
	. ./venv/bin/activate ; cat results/nl_french_cql.tsv | python cqlcmp.py > results/nl_french_cql_eval.tsv 2> results/nl_french_cql_eval.err

cqlcmp: results/nl_czech_cql_eval.tsv results/nl_english_cql_eval.tsv results/nl_french_cql_eval.tsv
