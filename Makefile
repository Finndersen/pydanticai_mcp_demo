.PHONY: install lint format test clean compile typecheck

# Compile dependency lock files
compile:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip compile pyproject.toml --extra dev -o requirements-dev.txt

# Install development dependencies from lockfile
install:
	uv pip install -r requirements-dev.txt
	uv pip install -e .
	@echo "Installation complete. You can now run 'dev' command."

# Run linting checks
lint:
	ruff check .
	ruff format . --check
	python -m pyright

# Format code
format:
	ruff check . --fix
	ruff format .

# Run tests with coverage
test:
	pytest --cov=src tests/
