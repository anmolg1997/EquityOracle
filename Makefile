SHELL := /bin/bash

REDIS_URL ?= redis://localhost:6379/0
PROJECT_NAME ?= equityoracle

.PHONY: help cache-clear-scan cache-clear-ui cache-clear-app reset-soft reset-hard clean-py clean-node

help:
	@echo "EquityOracle maintenance commands"
	@echo ""
	@echo "Safe defaults:"
	@echo "  make cache-clear-scan   # Clear scanner cache keys (ep:scan:*)"
	@echo "  make cache-clear-ui     # Clear frontend build/Vite caches"
	@echo "  make clean-py           # Remove Python cache artifacts"
	@echo "  make reset-soft         # Safe combined reset (scanner/ui/python caches)"
	@echo ""
	@echo "Advanced (destructive):"
	@echo "  make cache-clear-app    # Clear all app Redis keys (ep:*)"
	@echo "  make reset-hard         # docker compose down -v (wipes DB + Redis volumes)"
	@echo ""
	@echo "Optional:"
	@echo "  make clean-node         # Remove frontend node_modules and reinstall lockfile deps"

cache-clear-scan:
	@echo "Clearing Redis scanner keys (ep:scan:*)..."
	@keys=$$(redis-cli -u "$(REDIS_URL)" --scan --pattern 'ep:scan:*'); \
	if [[ -z "$$keys" ]]; then \
		echo "No scanner cache keys found."; \
	else \
		for k in $$keys; do redis-cli -u "$(REDIS_URL)" DEL "$$k" >/dev/null; done; \
		echo "Scanner cache cleared."; \
	fi

cache-clear-ui:
	@echo "Clearing frontend build caches..."
	@rm -rf frontend/dist frontend/node_modules/.vite
	@echo "Frontend cache artifacts removed."
	@echo "Note: Browser localStorage is not cleared by Make."

cache-clear-app:
	@echo "WARNING: Clearing all app-prefixed Redis keys (ep:*)."
	@keys=$$(redis-cli -u "$(REDIS_URL)" --scan --pattern 'ep:*'); \
	if [[ -z "$$keys" ]]; then \
		echo "No app Redis keys found."; \
	else \
		for k in $$keys; do redis-cli -u "$(REDIS_URL)" DEL "$$k" >/dev/null; done; \
		echo "All app Redis keys cleared."; \
	fi

clean-py:
	@echo "Removing Python cache artifacts..."
	@find backend -type d -name __pycache__ -prune -exec rm -rf {} +
	@find backend -type d -name .pytest_cache -prune -exec rm -rf {} +
	@rm -f backend/.coverage backend/coverage.xml
	@echo "Python caches removed."

clean-node:
	@echo "Removing frontend node_modules..."
	@rm -rf frontend/node_modules
	@cd frontend && npm ci
	@echo "Node modules reinstalled."

reset-soft: cache-clear-scan cache-clear-ui clean-py
	@echo "Soft reset complete."
	@echo "Tip: hard refresh the browser to clear in-memory UI state."

reset-hard:
	@echo "DANGER: This will run 'docker compose down -v' and wipe Postgres/Redis volumes."
	@docker compose down -v
	@echo "Hard reset complete."
