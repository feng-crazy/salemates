.PHONY: dev build test lint clean install

dev:
	@echo "Starting development environment..."
	docker-compose up -d

build:
	docker-compose build

test:
	pytest tests/ -v --cov=salesmate

lint:
	ruff check .
	ruff format --check .

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .ruff_cache .coverage

install:
	pip install -e ".[dev,test,feishu]"
