.PHONY: install lint format clean compile run

# Compile dependency lock files
compile:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip compile pyproject.toml --extra dev -o requirements-dev.txt

# Install development dependencies from lockfile
install:
	uv venv --python 3.11
	uv pip install -r requirements-dev.txt
	cd server && npm install

# Run linting checks for agent client
lint:
	ruff check client --fix
	ruff format client
	python -m pyright


run:
	@PYTHONPATH=${PYTHONPATH}:${PWD}/client && python client/mcp_agent/cli.py