.PHONY: check test run migrate
check: ## tests + ROOTS gate; exits non-zero on either failure
	./scripts/check.sh
test:
	.venv/bin/python -m pytest -q
migrate: ## apply pending schema migrations to ERPSIM_DATABASE_URL
	./scripts/migrate.sh
run:
	.venv/bin/uvicorn erpsim.main:app --reload --app-dir src
