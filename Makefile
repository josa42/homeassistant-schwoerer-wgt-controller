.PHONY: help venv install test lint clean dev-up dev-down dev-logs dev-restart sort-translations

PYTHON := $(shell command -v python3 || command -v python)
VENV := venv
VENV_BIN := $(VENV)/bin
VENV_PYTHON := $(VENV_BIN)/python
VENV_PIP := $(VENV_BIN)/pip

help:
	@echo "Available commands:"
	@echo ""
	@echo "Development:"
	@echo "  make dev-up       - Start local Home Assistant for testing"
	@echo "  make dev-down     - Stop local Home Assistant"
	@echo "  make dev-logs     - Follow Home Assistant logs"
	@echo "  make dev-restart  - Restart after code changes"
	@echo ""
	@echo "Testing:"
	@echo "  make venv     - Create virtual environment"
	@echo "  make install  - Install test dependencies (creates venv if needed)"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run linter"
	@echo "  make clean    - Clean cache files"
	@echo ""
	@echo "Translations:"
	@echo "  make sort-translations - Sort translation files alphabetically"

venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Creating virtual environment..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "Virtual environment created at ./$(VENV)"; \
		echo "To activate: source $(VENV_BIN)/activate"; \
	else \
		echo "Virtual environment already exists"; \
	fi

install: venv
	@echo "Installing dependencies in virtual environment..."
	$(VENV_PIP) install --upgrade pip
	$(VENV_PIP) install -r requirements_test.txt
	$(VENV_PIP) install ruff
	@echo "Done! Activate with: source $(VENV_BIN)/activate"

test:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	$(VENV_PYTHON) -m pytest tests/ -v

lint:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	$(VENV_BIN)/ruff check custom_components/ tests/

lint-fix:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make install' first."; \
		exit 1; \
	fi
	$(VENV_BIN)/ruff check --fix custom_components/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf $(VENV)

dev-up:
	@echo "Starting Home Assistant..."
	@echo "Setting up configuration..."
	@mkdir -p config
	@cp -n config.template.yaml config/configuration.yaml 2>/dev/null || true
	@touch config/automations.yaml config/scripts.yaml config/scenes.yaml config/secrets.yaml 2>/dev/null || true
	@mkdir -p config/themes
	docker compose up -d --force-recreate
	@echo ""
	@echo "✓ Home Assistant started successfully!"
	@echo "  Access at: http://localhost:8124"
	@echo ""
	@echo "View logs with: make dev-logs"
	@echo "Stop with:      make dev-down"

dev-down:
	docker compose down

dev-logs:
	@echo "Following logs (use Ctrl+C to stop or run: docker compose logs -f directly)..."
	@bash -c 'trap exit SIGINT; docker compose logs -f'

dev-restart:
	@echo "Restarting Home Assistant (this will recreate the container)..."
	docker compose up -d --force-recreate
	@echo ""
	@echo "✓ Container restarted!"
	@echo "View logs with: make dev-logs"

sort-translations:
	@echo "Sorting translation files..."
	@$(PYTHON) scripts/sort_translations.py
