.PHONY: help install-frontend install-backend install dev-up dev-down dev-backend dev-frontend \
        setup-db test-backend lint-frontend build-frontend deploy deploy-frontend smoke-test \
        deploy-agentcore wire-agentcore clean

BACKEND_DIR    := backend
FRONTEND_DIR   := frontend
INFRA_DIR      := infra
AGENTCORE_DIR  := PlatformAdvisorAgent
STACK_NAME     := platform-advisor
ENV            ?= dev

help:
	@echo "Platform Advisor — Available targets:"
	@echo ""
	@echo "  install               Install all dependencies"
	@echo "  install-frontend      Install Next.js deps"
	@echo "  install-backend       Install Python deps"
	@echo ""
	@echo "  dev-up                Start Docker (DynamoDB Local + API)"
	@echo "  dev-down              Stop Docker"
	@echo "  dev-backend           Run FastAPI with hot-reload (local, no Docker)"
	@echo "  dev-frontend          Run Next.js dev server"
	@echo "  setup-db              Create DynamoDB Local table + seed demo data"
	@echo ""
	@echo "  test-backend          Run pytest"
	@echo "  lint-frontend         Run ESLint + TypeScript check"
	@echo "  build-frontend        Build Next.js for production"
	@echo ""
	@echo "  deploy ENV=prod       SAM deploy Lambda + API GW + DynamoDB"
	@echo "  deploy-frontend       Build, sync to S3, invalidate CF, run smoke test"
	@echo "  smoke-test            Run post-deploy smoke test (real Cognito auth)"
	@echo "  deploy-agentcore      Deploy Strands agent to AgentCore Runtime (CodeZip)"
	@echo "  wire-agentcore        Update Lambda stack with AgentCore Runtime ARN"
	@echo "  clean                 Remove build artefacts"

# ── Install ───────────────────────────────────────────────────────────────────

install-frontend:
	cd $(FRONTEND_DIR) && npm install

install-backend:
	cd $(BACKEND_DIR) && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt

install: install-frontend install-backend

# ── Local dev ─────────────────────────────────────────────────────────────────

dev-up:
	docker compose up -d
	@echo "Waiting for DynamoDB Local..."
	@sleep 3
	$(MAKE) setup-db

dev-down:
	docker compose down

dev-backend:
	cd $(BACKEND_DIR) && \
	DEV_MODE=true \
	ENV=dev \
	DYNAMODB_TABLE=platform-advisor-main \
	DYNAMODB_ENDPOINT=http://localhost:8000 \
	AWS_REGION=us-east-1 \
	AWS_ACCESS_KEY_ID=local \
	AWS_SECRET_ACCESS_KEY=local \
	ALLOWED_ORIGINS=http://localhost:3000 \
	PYTHONPATH=. \
	.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

setup-db:
	AWS_ACCESS_KEY_ID=local \
	AWS_SECRET_ACCESS_KEY=local \
	python $(INFRA_DIR)/setup-local-db.py

# ── Quality ───────────────────────────────────────────────────────────────────

test-backend:
	cd $(BACKEND_DIR) && \
	DEV_MODE=true \
	PYTHONPATH=. \
	.venv/bin/pytest tests/ -v

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint && npx tsc --noEmit

build-frontend:
	cd $(FRONTEND_DIR) && npm run build

# ── Deploy ────────────────────────────────────────────────────────────────────

S3_BUCKET    := platform-advisor-frontend-dev-616627284001
CF_DIST_ID   := E33AR847I77OZS

deploy-frontend: build-frontend
	@echo "Syncing to S3..."
	aws s3 sync $(FRONTEND_DIR)/out/ s3://$(S3_BUCKET)/ --delete --quiet --profile platform-advisor
	@echo "Invalidating CloudFront..."
	aws cloudfront create-invalidation --distribution-id $(CF_DIST_ID) --paths "/*" \
	  --profile platform-advisor --query 'Invalidation.Id' --output text
	@echo "Waiting 15s for propagation..."
	@sleep 15
	@echo "Running smoke test..."
	$(MAKE) smoke-test

smoke-test:
	python3 smoke_test.py

deploy:
	cd $(INFRA_DIR) && sam build --skip-pull-image && sam deploy \
		--stack-name $(STACK_NAME)-$(ENV) \
		--parameter-overrides Env=$(ENV) \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--profile platform-advisor \
		--region us-east-1 \
		--no-fail-on-empty-changeset

# Deploy the Strands agent pipeline to Amazon Bedrock AgentCore Runtime.
# Uses CodeZip (no Docker required).  Reads account/region from agentcore/aws-targets.json.
deploy-agentcore:
	@echo "Deploying Platform Advisor agent to AgentCore Runtime..."
	cd $(AGENTCORE_DIR) && \
	AWS_PROFILE=platform-advisor \
	agentcore deploy -y
	@echo ""
	@echo "Deployment complete.  Run 'make wire-agentcore' to update the Lambda stack."

# After deploy-agentcore, retrieve the Runtime ARN and update the Lambda stack.
wire-agentcore:
	@echo "Fetching AgentCore Runtime ARN..."
	$(eval AGENT_ARN := $(shell cd $(AGENTCORE_DIR) && AWS_PROFILE=platform-advisor agentcore status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agentRuntimeArn',''))" 2>/dev/null))
	@if [ -z "$(AGENT_ARN)" ]; then \
		echo "ERROR: could not retrieve AgentCore Runtime ARN. Run 'make deploy-agentcore' first."; \
		exit 1; \
	fi
	@echo "AgentCore Runtime ARN: $(AGENT_ARN)"
	cd $(INFRA_DIR) && sam deploy \
		--stack-name $(STACK_NAME)-$(ENV) \
		--parameter-overrides Env=$(ENV) AgentCoreRuntimeArn="$(AGENT_ARN)" \
		--capabilities CAPABILITY_IAM \
		--resolve-s3 \
		--profile platform-advisor \
		--region us-east-1 \
		--no-fail-on-empty-changeset
	@echo "Lambda stack updated with AgentCore Runtime ARN."

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	cd $(FRONTEND_DIR) && rm -rf .next node_modules
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	cd $(INFRA_DIR) && rm -rf .aws-sam 2>/dev/null || true
