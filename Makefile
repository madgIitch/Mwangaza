.PHONY: lint typecheck test frontend-lint frontend-typecheck frontend-test frontend-build

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
PYTHON ?= uv run python
PYTHONPATH_ENV = $$env:PYTHONPATH='src'; $$env:UV_CACHE_DIR='.cache/uv';
RUNPY = & $(PYTHON)
else
PYTHON ?= python
PYTHONPATH_ENV = PYTHONPATH=src
RUNPY = $(PYTHON)
endif

lint:
	$(PYTHONPATH_ENV) $$env:PYTHONPYCACHEPREFIX='.cache/pycache-lint'; $(RUNPY) -m compileall -q src tests app.py

typecheck:
	$(PYTHONPATH_ENV) $$env:PYTHONPYCACHEPREFIX='.cache/pycache-typecheck'; $(RUNPY) -m compileall -q src tests app.py

test:
	$(PYTHONPATH_ENV) $$env:PYTHONPYCACHEPREFIX='.cache/pycache-test'; $(RUNPY) -m unittest discover -s tests

frontend-lint:
	npm run lint

frontend-typecheck:
	npm run typecheck

frontend-test:
	npm test

frontend-build:
	npm run build
