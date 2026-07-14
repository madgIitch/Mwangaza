.PHONY: lint typecheck test

ifeq ($(OS),Windows_NT)
SHELL := powershell.exe
.SHELLFLAGS := -NoProfile -ExecutionPolicy Bypass -Command
WIN_LOCALAPPDATA := $(subst \,/,$(LOCALAPPDATA))
PYTHON ?= $(shell powershell.exe -NoProfile -Command "(Get-ChildItem -Path '$(WIN_LOCALAPPDATA)/Python/pythoncore-*/python.exe' | Select-Object -First 1 -ExpandProperty FullName).Replace('\','/')")
PYTHONPATH_ENV = $$env:PYTHONPATH='src';
RUNPY = & $(PYTHON)
else
PYTHON ?= python
PYTHONPATH_ENV = PYTHONPATH=src
RUNPY = $(PYTHON)
endif

lint:
	$(PYTHONPATH_ENV) $(RUNPY) -m compileall -q src tests app.py

typecheck:
	$(PYTHONPATH_ENV) $(RUNPY) -m compileall -q src tests app.py

test:
	$(PYTHONPATH_ENV) $(RUNPY) -m unittest discover -s tests
