.PHONY: install lint format clean compile run

# Compile dependency lock files
compile:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip compile pyproject.toml --extra dev -o requirements-dev.txt

# Install development dependencies from lockfile
install:
	uv pip install -r requirements-dev.txt
	uv pip install -e .
	cd server && npm install

# Run linting checks for agent client
lint:
	ruff check client
	ruff format client --check
	python -m pyright

# Format code for agent client
format:
	ruff format client
	ruff check client --fix

run:
	@PYTHONPATH=${PYTHONPATH}:${PWD}/client && python client/mcp_agent/cli.py