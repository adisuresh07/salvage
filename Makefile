.PHONY: bootstrap doctor generate check test demo dev api worker console-build docker

bootstrap:
	uv sync --all-groups
	pnpm --dir console install

doctor:
	uv run salvage doctor

generate:
	uv run python scripts/generate_openapi.py
	pnpm --dir console exec openapi-typescript ../openapi.json -o src/api/schema.d.ts

check:
	uv run ruff format --check src scripts tests
	uv run ruff check src scripts tests
	uv run mypy src/salvage
	uv run pytest
	pnpm --dir console test
	pnpm --dir console build

test:
	uv run pytest

demo:
	SALVAGE_LLM=cache-only uv run salvage demo

dev:
	SALVAGE_LLM=cache-only uv run salvage demo
	uv run uvicorn salvage.api.app:app --reload --port 8000

api:
	uv run uvicorn salvage.api.app:app --host 0.0.0.0 --port 8000

worker:
	uv run salvage work --loop

console-build:
	pnpm --dir console build

docker:
	docker compose up --build
