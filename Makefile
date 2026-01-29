requirements:
	poetry install --no-root --with dev
	# pre-commit install --install-hooks
	export BETTER_EXCEPTIONS=1

isort:
	pre-commit run --all isort

black:
	pre-commit run --all black

pycln:
	pre-commit run --all pycln

flake8:
	pre-commit run --all flake8

mypy:
	pre-commit run --all mypy

pytest:
	poetry run pytest tests --cov-config=.coveragerc --cov-fail-under=50 --cov=app --cov-report term-missing

run-all-pre-commit-hooks:
	pre-commit run --all

check: run-all-pre-commit-hooks pytest

## Commands for other projects local development environments
migrations:
	poetry run alembic upgrade head

start-db:
	docker-compose up -d db

main:
	poetry run python3 main.py

sync-ats:
	poetry run python3 -m app.workers.sync_ats > scrapping_ats_logs.txt

sync-linkedin:
	poetry run python3 -m app.workers.sync_linkedin > scrapping_linkedin_logs.txt

sync-all:
	poetry run python3 -m app.workers.sync_all > scrapping_logs.txt

analyse:
	poetry run python3 -m app.workers.job_analyser

create-user:
	poetry run python3 -m app.workers.create_user --name "$(name)" --email "$(email)"

seed-career-pages:
	poetry run python3 -m app.workers.seed_career_pages

backfill-job-career-page:
	poetry run python3 -m app.workers.backfill_job_career_page

urlscan-first-level:
	poetry run python3 -m app.seeds.url_scan_client $(domain)

start: requirements start-db migrations main
