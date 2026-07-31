.PHONY: help install-frontend install-backend install dev-up dev-down dev-backend dev-frontend \
        setup-db test-backend lint-frontend check-frontend-production-env build-frontend \
        check-deploy-config deploy deploy-frontend smoke-test prepare-lambda \
        check-agentcore-cli deploy-agentcore wire-agentcore seed-demo clean

BACKEND_DIR    := backend
FRONTEND_DIR   := frontend
INFRA_DIR      := infra
AGENTCORE_DIR  := PlatformAdvisorAgent
AGENT_APP_DIR  := $(AGENTCORE_DIR)/app/PlatformAdvisorAgent
LAMBDA_STAGE   := $(INFRA_DIR)/.lambda-src
STACK_NAME     := platform-advisor
ENV            ?= dev
ADMIN_ALIASES  ?= aigopala,thandavm
AWS_PROFILE    ?= platform-advisor
AWS_REGION     ?= us-east-1
AGENTCORE_UV_CACHE_DIR ?= /tmp/platform-advisor-uv-cache

# Browser-facing deployment configuration. Every NEXT_PUBLIC value used by the
# frontend is injected explicitly so Next.js cannot publish .env.local values.
FRONTEND_API_URL              ?= https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1
FRONTEND_APP_URL              ?= https://d1wa5bvm23hhld.cloudfront.net
COGNITO_USER_POOL_ID          ?= us-east-1_oSEwvKdfd
COGNITO_CLIENT_ID             ?= 6gbe6mt1il74sdqlq8boc60ld4
COGNITO_DOMAIN                ?= platform-advisor-dev-616627284001.auth.us-east-1.amazoncognito.com
COGNITO_IDENTITY_POOL_ID      ?= us-east-1:7494c292-da32-4ddf-b573-a4729ad4aeaf
AGENTCORE_RUNTIME_ARN         ?= arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/PlatformAdvisorAgent_PlatformAdvisorAgent-3U71dVBprI
FRONTEND_DEV_MODE             ?= false

# @aws/agentcore and the obsolete Python starter toolkit install the same
# command name. Prefer Homebrew's Node CLI, then fall back to PATH.
AGENTCORE_CLI ?= $(shell if [ -x /opt/homebrew/bin/agentcore ]; then \
	printf '%s' /opt/homebrew/bin/agentcore; \
else \
	command -v agentcore 2>/dev/null; \
fi)

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
	@echo "  seed-demo             Generate demo portfolio (dry-run unless DEMO_APPLY=1)"
	@echo ""
	@echo "  test-backend          Run pytest"
	@echo "  lint-frontend         Run ESLint + TypeScript check"
	@echo "  build-frontend        Build Next.js with explicit production browser config"
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
	PYTHONPATH=.:../PlatformAdvisorAgent/app/PlatformAdvisorAgent \
	.venv/bin/uvicorn api.main:app --host 0.0.0.0 --port 8080 --reload

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

setup-db:
	AWS_ACCESS_KEY_ID=local \
	AWS_SECRET_ACCESS_KEY=local \
	python $(INFRA_DIR)/setup-local-db.py

DEMO_TARGET       ?= local
DEMO_APPLY        ?= 0
DEMO_CONFIRM      ?=
DEMO_PROFILE      ?= platform-advisor
DEMO_REGION       ?= us-east-1
DEMO_TABLE        ?= platform-advisor-main
DEMO_ENDPOINT     ?= http://localhost:8000
DEMO_APPLY_FLAG   = $(if $(filter 1 true yes,$(DEMO_APPLY)),--apply,)
DEMO_CONFIRM_FLAG = $(if $(strip $(DEMO_CONFIRM)),--confirm $(DEMO_CONFIRM),)

seed-demo:
	PYTHONPATH=$(BACKEND_DIR):$(AGENT_APP_DIR) \
	uv run --with-requirements $(BACKEND_DIR)/requirements.txt \
	python -m demo.seed \
		--target $(DEMO_TARGET) \
		--profile $(DEMO_PROFILE) \
		--region $(DEMO_REGION) \
		--table $(DEMO_TABLE) \
		--endpoint $(DEMO_ENDPOINT) \
		$(DEMO_APPLY_FLAG) $(DEMO_CONFIRM_FLAG)

# ── Quality ───────────────────────────────────────────────────────────────────

test-backend:
	cd $(BACKEND_DIR) && \
	DEV_MODE=true \
	PYTHONPATH=. \
	.venv/bin/pytest tests/ -v

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint && npx tsc --noEmit

check-frontend-production-env:
	@set -eu; \
	for entry in \
		'NEXT_PUBLIC_API_URL=$(FRONTEND_API_URL)' \
		'NEXT_PUBLIC_APP_URL=$(FRONTEND_APP_URL)' \
		'NEXT_PUBLIC_COGNITO_USER_POOL_ID=$(COGNITO_USER_POOL_ID)' \
		'NEXT_PUBLIC_USER_POOL_ID=$(COGNITO_USER_POOL_ID)' \
		'NEXT_PUBLIC_COGNITO_CLIENT_ID=$(COGNITO_CLIENT_ID)' \
		'NEXT_PUBLIC_COGNITO_DOMAIN=$(COGNITO_DOMAIN)' \
		'NEXT_PUBLIC_IDENTITY_POOL_ID=$(COGNITO_IDENTITY_POOL_ID)' \
		'NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN=$(AGENTCORE_RUNTIME_ARN)' \
		'NEXT_PUBLIC_AWS_REGION=$(AWS_REGION)' \
		'NEXT_PUBLIC_DEV_MODE=$(FRONTEND_DEV_MODE)'; do \
		name=$${entry%%=*}; \
		value=$${entry#*=}; \
		if [ -z "$$value" ]; then \
			echo "ERROR: $$name must be set for a production frontend build."; \
			exit 1; \
		fi; \
		case "$$value" in \
			*localhost*|*127.0.0.1*|*0.0.0.0*) \
				echo "ERROR: $$name contains a local address: $$value"; \
				exit 1 ;; \
		esac; \
	done; \
	if [ "$(FRONTEND_DEV_MODE)" != "false" ]; then \
		echo "ERROR: NEXT_PUBLIC_DEV_MODE must be false for a production frontend build."; \
		exit 1; \
	fi

build-frontend: check-frontend-production-env
	cd $(FRONTEND_DIR) && \
	NEXT_PUBLIC_API_URL="$(FRONTEND_API_URL)" \
	NEXT_PUBLIC_APP_URL="$(FRONTEND_APP_URL)" \
	NEXT_PUBLIC_COGNITO_USER_POOL_ID="$(COGNITO_USER_POOL_ID)" \
	NEXT_PUBLIC_USER_POOL_ID="$(COGNITO_USER_POOL_ID)" \
	NEXT_PUBLIC_COGNITO_CLIENT_ID="$(COGNITO_CLIENT_ID)" \
	NEXT_PUBLIC_COGNITO_DOMAIN="$(COGNITO_DOMAIN)" \
	NEXT_PUBLIC_IDENTITY_POOL_ID="$(COGNITO_IDENTITY_POOL_ID)" \
	NEXT_PUBLIC_AGENTCORE_RUNTIME_ARN="$(AGENTCORE_RUNTIME_ARN)" \
	NEXT_PUBLIC_AWS_REGION="$(AWS_REGION)" \
	NEXT_PUBLIC_DEV_MODE="$(FRONTEND_DEV_MODE)" \
	npm run build
	@if rg -n -I 'https?://(localhost|127\.0\.0\.1|0\.0\.0\.0)(:[0-9]+)?' $(FRONTEND_DIR)/out; then \
		echo "ERROR: generated frontend contains a local URL; refusing to publish."; \
		exit 1; \
	fi

# ── Deploy ────────────────────────────────────────────────────────────────────

S3_BUCKET    := platform-advisor-frontend-dev-616627284001
CF_DIST_ID   := E33AR847I77OZS

deploy-frontend: build-frontend
	@test -f $(FRONTEND_DIR)/out/architecture/index.html || \
		(echo "ERROR: architecture/index.html is missing from the frontend export."; exit 1)
	@echo "Syncing to S3..."
	aws s3 sync $(FRONTEND_DIR)/out/ s3://$(S3_BUCKET)/ --delete --quiet --profile $(AWS_PROFILE)
	@echo "Invalidating CloudFront..."
	aws cloudfront create-invalidation --distribution-id $(CF_DIST_ID) --paths "/*" \
	  --profile $(AWS_PROFILE) --query 'Invalidation.Id' --output text
	@echo "Waiting 15s for propagation..."
	@sleep 15
	@echo "Running smoke test..."
	$(MAKE) smoke-test \
		AWS_PROFILE="$(AWS_PROFILE)" \
		AWS_REGION="$(AWS_REGION)" \
		API_URL="$(FRONTEND_API_URL)" \
		CF_URL="$(FRONTEND_APP_URL)" \
		S3_BUCKET="$(S3_BUCKET)"

smoke-test:
	AWS_PROFILE="$(AWS_PROFILE)" \
	AWS_REGION="$(AWS_REGION)" \
	API_URL="$(FRONTEND_API_URL)" \
	CF_URL="$(FRONTEND_APP_URL)" \
	S3_BUCKET="$(S3_BUCKET)" \
	uv run --no-project --with boto3 python smoke_test.py

prepare-lambda:
	@echo "Preparing Lambda source..."
	rm -rf $(LAMBDA_STAGE)
	mkdir -p $(LAMBDA_STAGE)
	rsync -a \
		--exclude='.venv/' \
		--exclude='.pytest_cache/' \
		--exclude='__pycache__/' \
		--exclude='*.pyc' \
		$(BACKEND_DIR)/ $(LAMBDA_STAGE)/
	for package in advisor_core pipeline_skills agent_core_engine mcp_client knowledge_base; do \
		rsync -a \
			--exclude='__pycache__/' \
			--exclude='*.pyc' \
			$(AGENT_APP_DIR)/$$package/ $(LAMBDA_STAGE)/$$package/; \
	done

check-deploy-config:
	@case "$(AGENTCORE_RUNTIME_ARN)" in \
		"" ) \
			if [ "$(ENV)" = "prod" ]; then \
				echo "ERROR: AGENTCORE_RUNTIME_ARN is required for ENV=prod; an empty value would remove browser invoke permission."; \
				exit 1; \
			fi ;; \
		arn:*:bedrock-agentcore:*:*:runtime/* ) ;; \
		* ) \
			echo "ERROR: AGENTCORE_RUNTIME_ARN is not a valid AgentCore Runtime ARN."; \
			exit 1 ;; \
	esac

deploy: check-deploy-config prepare-lambda
	cd $(INFRA_DIR) && sam build --skip-pull-image && sam deploy \
		--stack-name $(STACK_NAME)-$(ENV) \
		--parameter-overrides \
			Env="$(ENV)" \
			AllowedOrigins="$(FRONTEND_APP_URL)" \
			DevMode="$(FRONTEND_DEV_MODE)" \
			AdminAlias="$(ADMIN_ALIASES)" \
			AgentCoreRuntimeArn="$(AGENTCORE_RUNTIME_ARN)" \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--resolve-s3 \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION) \
		--no-fail-on-empty-changeset

# Deploy the Strands agent pipeline to Amazon Bedrock AgentCore Runtime.
# Uses CodeZip (no Docker required).  Reads account/region from agentcore/aws-targets.json.
check-agentcore-cli:
	@if [ -z "$(AGENTCORE_CLI)" ] || [ ! -x "$(AGENTCORE_CLI)" ]; then \
		echo "ERROR: @aws/agentcore CLI not found. Install it with: npm install -g @aws/agentcore"; \
		exit 1; \
	fi
	@version="$$("$(AGENTCORE_CLI)" --version 2>/dev/null)" || { \
		echo "ERROR: $(AGENTCORE_CLI) is not the @aws/agentcore Node CLI (the obsolete Python starter toolkit may be first on PATH)."; \
		exit 1; \
	}; \
	case "$$version" in \
		[0-9]*.[0-9]*.[0-9]*) ;; \
		*) echo "ERROR: unexpected @aws/agentcore version output: $$version"; exit 1 ;; \
	esac; \
	if ! "$(AGENTCORE_CLI)" deploy --help 2>&1 | rg -q 'Deploy project infrastructure to AWS via CDK'; then \
		echo "ERROR: $(AGENTCORE_CLI) does not expose the expected @aws/agentcore deploy command."; \
		exit 1; \
	fi; \
	if [ ! -f "$(AGENTCORE_DIR)/agentcore/agentcore.json" ]; then \
		echo "ERROR: $(AGENTCORE_DIR)/agentcore/agentcore.json is missing."; \
		exit 1; \
	fi; \
	echo "Using @aws/agentcore $$version: $(AGENTCORE_CLI)"

deploy-agentcore: check-agentcore-cli
	@echo "Deploying Platform Advisor agent to AgentCore Runtime..."
	cd $(AGENTCORE_DIR) && \
	UV_CACHE_DIR="$(AGENTCORE_UV_CACHE_DIR)" \
	AWS_PROFILE=$(AWS_PROFILE) \
	"$(AGENTCORE_CLI)" deploy -y
	@echo ""
	@echo "Deployment complete.  Run 'make wire-agentcore' to update the Lambda stack."

# After deploy-agentcore, retrieve the Runtime ARN and update the Lambda stack.
wire-agentcore: check-agentcore-cli
	@echo "Fetching AgentCore Runtime ARN..."
	$(eval AGENT_ARN := $(shell cd $(AGENTCORE_DIR) && AWS_PROFILE=$(AWS_PROFILE) "$(AGENTCORE_CLI)" status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(next((r.get('identifier','') for r in d.get('resources',[]) if r.get('resourceType') == 'agent'), ''))" 2>/dev/null))
	@if [ -z "$(AGENT_ARN)" ]; then \
		echo "ERROR: could not retrieve AgentCore Runtime ARN. Run 'make deploy-agentcore' first."; \
		exit 1; \
	fi
	@echo "AgentCore Runtime ARN: $(AGENT_ARN)"
	cd $(INFRA_DIR) && sam deploy \
		--stack-name $(STACK_NAME)-$(ENV) \
		--parameter-overrides Env=$(ENV) AgentCoreRuntimeArn="$(AGENT_ARN)" \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--resolve-s3 \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION) \
		--no-fail-on-empty-changeset
	@echo "Lambda stack updated with AgentCore Runtime ARN."

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	cd $(FRONTEND_DIR) && rm -rf .next node_modules
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	cd $(INFRA_DIR) && rm -rf .aws-sam .lambda-src 2>/dev/null || true
