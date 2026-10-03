.PHONY: install check lint typecheck test format phase0

install:
	python -m pip install -e ".[dev]"

lint:
	ruff check backend

format:
	ruff format backend

typecheck:
	mypy

test:
	pytest

check: lint typecheck test

phase0: check
	@echo "Phase 0 checks passed"
