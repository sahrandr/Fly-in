PYTHON ?= python3
MAIN   := main.py

.PHONY: install run debug clean lint lint-strict

# Install runtime (raylib provides the `pyray` module) and lint dependencies.
# Tip: activate a virtual environment first (see README).
install:
	$(PYTHON) -m pip install raylib flake8 mypy

# Launch the simulation (title screen -> map selection -> animation).
run:
	$(PYTHON) $(MAIN)

# Same as `run`, inside the built-in Python debugger.
debug:
	$(PYTHON) -m pdb $(MAIN)

# Remove caches and temporary files.
clean:
	find . -type d \( -name __pycache__ -o -name .mypy_cache -o -name .pytest_cache \) -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

lint:
	flake8 .
	mypy . --warn-return-any --warn-unused-ignores --ignore-missing-imports --disallow-untyped-defs --check-untyped-defs

lint-strict:
	flake8 .
	mypy . --strict
