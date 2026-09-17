.PHONY: check test run
check: ## tests + ROOTS gate; exits non-zero on either failure
	./scripts/check.sh
test:
	.venv/bin/python -m pytest -q
run:
	.venv/bin/uvicorn erpsim.main:app --reload --app-dir src
