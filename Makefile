.PHONY: data test lint format

PYTHON ?= .venv/bin/python

data:
	$(PYTHON) experiments/scripts/build_datasets.py

test:
	$(PYTHON) -m coverage run -m pytest
	$(PYTHON) -m coverage report

lint:
	$(PYTHON) -m ruff check .
	find src tests experiments/scripts -type f -name '*.py' -print0 | \
		xargs -0 -n 1 $(PYTHON) -m black --check --quiet

format:
	find src tests experiments/scripts -type f -name '*.py' -print0 | \
		xargs -0 -n 1 $(PYTHON) -m black --quiet
	$(PYTHON) -m ruff check --fix .
