.PHONY: jupyter venv login

venv: .venv
.venv: 
	python3 -m venv .venv
	. .venv/bin/activate; pip install -r requirements.txt

login: .venv
	. .venv/bin/activate; HF_HOME=$(shell pwd)/.cache/ huggingface-cli login 

jupyter0: .venv
	. .venv/bin/activate; HF_HOME=$(shell pwd)/.cache/ CUDA_VISIBLE_DEVICES=0 jupyter lab --port 8890

jupyter1: .venv
	. .venv/bin/activate; HF_HOME=$(shell pwd)/.cache/ CUDA_VISIBLE_DEVICES=1 jupyter lab --port 8891

