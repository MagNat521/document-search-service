.PHONY: up down ingest reingest test docs logs ps

# Build images and start the whole stack (db, elasticsearch, app, ingest).
up:
	docker compose up -d --build

# Stop everything and remove volumes (wipes data).
down:
	docker compose down -v

# Run the one-off ingest job.
ingest:
	docker compose run --rm ingest

# Reload data from scratch.
reingest:
	docker compose run --rm ingest python -m scripts.ingest --csv data/posts.csv --recreate

# Run functional tests (needs db + elasticsearch running).
test:
	pytest

# Regenerate docs.json from the live app schema.
docs:
	python -m scripts.export_openapi

logs:
	docker compose logs -f app

ps:
	docker compose ps
