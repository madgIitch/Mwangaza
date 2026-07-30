.PHONY: lint typecheck test test-contract test-frontend test-somalia-scenario demo-somalia coverage quality-gate frontend-lint frontend-typecheck frontend-test frontend-build container-smoke scheduled-refresh-dry-run

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
PYTHON ?= uv run python
COVERAGE_PYTHON ?= uv run --extra dev python
PYTHONPATH_ENV = $$env:PYTHONPATH='src'; $$env:UV_CACHE_DIR='.cache/uv';
PYCACHE_ENV = $$env:PYTHONPYCACHEPREFIX='.cache/pycache';
TEST_ENV = $$env:MWANGAZA_ENV='test'; $$env:MWANGAZA_GEE_PROJECT='replace-me'; $$env:MWANGAZA_GEE_SERVICE_ACCOUNT='replace-me'; $$env:MWANGAZA_GEE_PRIVATE_KEY_JSON='replace-me';
RUNPY = & $(PYTHON)
RUNCOVERAGE = & $(COVERAGE_PYTHON)
else
PYTHON ?= python
COVERAGE_PYTHON ?= $(PYTHON)
PYTHONPATH_ENV = PYTHONPATH=src
PYCACHE_ENV = PYTHONPYCACHEPREFIX=.cache/pycache
TEST_ENV = MWANGAZA_ENV=test MWANGAZA_GEE_PROJECT=replace-me MWANGAZA_GEE_SERVICE_ACCOUNT=replace-me MWANGAZA_GEE_PRIVATE_KEY_JSON=replace-me
RUNPY = $(PYTHON)
RUNCOVERAGE = $(COVERAGE_PYTHON)
endif

lint:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(RUNPY) -m compileall -q src tests app.py

typecheck:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(RUNPY) -m compileall -q src tests app.py

test:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(TEST_ENV) $(RUNPY) -m unittest discover -s tests

test-contract:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(TEST_ENV) $(RUNPY) -m unittest tests.contracts.test_contracts tests.api.test_public_api

test-frontend:
	npm test -- --run tests/frontend/smoke.test.tsx

test-somalia-scenario:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(TEST_ENV) $(RUNPY) -m unittest tests.e2e.test_somalia_scenario

demo-somalia:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(RUNPY) scripts/demo_somalia.py

coverage:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(TEST_ENV) $(RUNCOVERAGE) -m coverage run -m unittest discover -s tests
	$(PYTHONPATH_ENV) $(RUNCOVERAGE) -m coverage report

quality-gate: lint typecheck test test-contract coverage frontend-lint frontend-typecheck frontend-test frontend-build

frontend-lint:
	npm run lint

frontend-typecheck:
	npm run typecheck

frontend-test:
	npm test

frontend-build:
	npm run build

container-smoke:
	$(RUNPY) scripts/smoke_containers.py

scheduled-refresh-dry-run:
	$(PYTHONPATH_ENV) $(PYCACHE_ENV) $(RUNPY) -m mwangaza.data.refresh --dry-run
