.PHONY: setup lint test build contract docs-check infra-plan deploy destroy
setup:
	cd backend && uv sync --extra dev --locked
	cd frontend && npm ci
lint:
	cd backend && uv run ruff check app tests
	cd frontend && npm run lint
test:
	cd backend && uv run pytest --cov=app
	cd frontend && npm test
build:
	cd frontend && npm run build
	podman compose build
contract:
	cd backend && uv run python scripts/export_openapi.py
	cd frontend && npm run contract
	git diff --exit-code -- backend/openapi.json frontend/src/generated/api.d.ts
docs-check:
	npm run docs:build
	npx --yes markdownlint-cli2 "docs/**/*.md"
infra-plan:
	terraform -chdir=infra/terraform init && terraform -chdir=infra/terraform plan
deploy:
	helm upgrade --install worldguessr infra/helm/worldguessr --namespace worldguessr --create-namespace
destroy:
	@echo "Review docs/04-cloud-deploy/README.md before running terraform destroy."
	terraform -chdir=infra/terraform destroy
