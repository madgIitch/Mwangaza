.PHONY: lint typecheck test

lint:
	python -m compileall -q src tests app.py

typecheck:
	python -m compileall -q src tests app.py

test:
	python -m unittest discover -s tests
