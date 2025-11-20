VENV := venv

# default target, when make executed without arguments
all: venv

$(VENV)/bin/activate: pyproject.toml
	python3 -m venv $(VENV)
	./$(VENV)/bin/pip install -e .[dev]
	chmod +x src/glacierPy/__main__.py

# venv is a shortcut target
venv: $(VENV)/bin/activate

run: venv
	./$(VENV)/bin/python3 -m glacierPy

test: venv
	./$(VENV)/bin/python3 -m unittest discover tests

lint: venv
	./$(VENV)/bin/mypy src/glacierPy

clean:
	rm -rf $(VENV)
	rm -rf src/*.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

.PHONY: all venv run clean