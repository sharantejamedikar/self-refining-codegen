.PHONY: test lint format

PYTHON ?= .venv/bin/python

test:
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m black --check .

format:
	$(PYTHON) -m black .
	$(PYTHON) -m ruff check --fix .
