.PHONY: install dev test lint typecheck fmt eval up down

install:
	pip install -e .

dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

lint:
	ruff check .

typecheck:
	mypy src

fmt:
	ruff format .

eval:
	contextflow evaluate --benchmark benchmarks/default.yaml

up:
	docker compose up -d

down:
	docker compose down
