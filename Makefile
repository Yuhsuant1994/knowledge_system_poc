.PHONY: up down logs pull-model fetch-sales hr-init hr-update test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

pull-model:
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-llama3.1:8b}
	docker compose exec ollama ollama pull $${EMBEDDING_MODEL:-nomic-embed-text}

fetch-sales:
	docker compose exec api python -m ingestion.sales_fetch

hr-init:
	docker compose exec api python -m ingestion.hr.init

hr-update:
	docker compose exec api python -m ingestion.hr.update

test:
	poetry run pytest
