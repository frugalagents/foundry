.PHONY: help install-frontend install-backend install dev-up dev-down dev-backend dev-frontend \
        setup-db test-backend lint-frontend check-frontend-production-env build-frontend \
        check-deploy-config check-admin-migration check-frontend-bucket deploy deploy-frontend \
        deploy-admin-migration-phase1 deploy-admin-migration-phase2 smoke-test prepare-lambda \
        configure-log-retention check-agentcore-cli deploy-agentcore wire-agentcore seed-demo clean

BACKEND_DIR    := backend
FRONTEND_DIR   := frontend
INFRA_DIR      := infra
AGENTCORE_DIR  := PlatformAdvisorAgent
AGENT_APP_DIR  := $(AGENTCORE_DIR)/app/PlatformAdvisorAgent
LAMBDA_STAGE   := $(INFRA_DIR)/.lambda-src
STACK_NAME     := platform-advisor
ENV            ?= dev
ADMIN_ALIASES  ?=
ADMIN_GROUP_NAME ?= admin
ADMIN_ALIAS_MIGRATION_ENABLED ?= false
ADMIN_ALIAS_MIGRATION_ACK ?=
ALLOW_NON_DEV_DEPLOY ?= false
LOG_RETENTION_DAYS ?= 30
MIDWAY_CLIENT_ID ?= platform-advisor-dev
MIDWAY_CLIENT_SECRET ?=
KNOWLEDGE_BASE_ID ?= EDDM8YZDNJ
AWS_PROFILE    ?= platform-advisor
AWS_REGION     ?= us-east-1
AGENTCORE_UV_CACHE_DIR ?= /tmp/platform-advisor-uv-cache
AGENTCORE_NETWORK_MODE ?= PUBLIC

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

export MIDWAY_CLIENT_SECRET

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
	@echo "  deploy                Validate and review a SAM change set before execution"
	@echo "  deploy-admin-migration-phase1  Create admin group with guarded dev fallback"
	@echo "  deploy-admin-migration-phase2  Disable fallback after group enrollment"
	@echo "  configure-log-retention  Apply and verify bounded Lambda log retention"
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
	fi; \
	if [ "$(ENV)" != "dev" ] && { \
		[ "$(FRONTEND_API_URL)" = "https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1" ] || \
		[ "$(FRONTEND_APP_URL)" = "https://d1wa5bvm23hhld.cloudfront.net" ] || \
		[ "$(COGNITO_USER_POOL_ID)" = "us-east-1_oSEwvKdfd" ] || \
		[ "$(COGNITO_CLIENT_ID)" = "6gbe6mt1il74sdqlq8boc60ld4" ] || \
		[ "$(COGNITO_IDENTITY_POOL_ID)" = "us-east-1:7494c292-da32-4ddf-b573-a4729ad4aeaf" ] || \
		[ "$(AGENTCORE_RUNTIME_ARN)" = "arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/PlatformAdvisorAgent_PlatformAdvisorAgent-3U71dVBprI" ] || \
		[ "$(S3_BUCKET)" = "platform-advisor-frontend-dev-616627284001" ] || \
		[ "$(CF_DIST_ID)" = "E33AR847I77OZS" ]; \
	}; then \
		echo "ERROR: ENV=$(ENV) frontend publish still points at the fixed dev estate."; \
		exit 1; \
	fi

build-frontend: check-frontend-production-env
	cd $(FRONTEND_DIR) && \
	rm -rf .next out && \
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

S3_BUCKET    ?= platform-advisor-frontend-dev-616627284001
CF_DIST_ID   ?= E33AR847I77OZS
FRONTEND_DEPLOYMENT_PREFIX ?= _deployments

check-frontend-bucket:
	@status="$$(aws s3api get-bucket-versioning \
		--bucket "$(S3_BUCKET)" \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)" \
		--query Status --output text)"; \
	if [ "$$status" != "Enabled" ]; then \
		echo "ERROR: s3://$(S3_BUCKET) must have versioning enabled before frontend deployment."; \
		echo "Deploy the reviewed SAM change set first."; \
		exit 1; \
	fi

deploy-frontend: build-frontend check-frontend-bucket
	@test -f $(FRONTEND_DIR)/out/architecture/index.html || \
		(echo "ERROR: architecture/index.html is missing from the frontend export."; exit 1)
	@set -eu; \
	deployment_id="$$(date -u +%Y%m%dT%H%M%SZ)"; \
	before_manifest="$$(mktemp)"; \
	head_response="$$(mktemp)"; \
	trap 'rm -f "$$before_manifest" "$$head_response"' EXIT; \
	aws s3api list-object-versions \
		--bucket "$(S3_BUCKET)" \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)" \
		--query 'Versions[?IsLatest==`true`].[Key,VersionId]' \
		--output json > "$$before_manifest"; \
	echo "Syncing frontend deployment $$deployment_id to versioned S3..."; \
	aws s3 sync $(FRONTEND_DIR)/out/ s3://$(S3_BUCKET)/ \
		--delete \
		--exclude "$(FRONTEND_DEPLOYMENT_PREFIX)/*" \
		--quiet \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)"; \
	entry_sha="$$(shasum -a 256 $(FRONTEND_DIR)/out/index.html | awk '{print $$1}')"; \
	aws s3 cp $(FRONTEND_DIR)/out/index.html s3://$(S3_BUCKET)/index.html \
		--metadata "deployment-sha256=$$entry_sha,deployment-id=$$deployment_id" \
		--content-type "text/html" \
		--cache-control "no-cache" \
		--quiet \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)"; \
	aws s3api head-object \
		--bucket "$(S3_BUCKET)" \
		--key index.html \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)" \
		--output json > "$$head_response"; \
	python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); expected=sys.argv[2]; assert d.get("VersionId") not in (None, "", "null"), "index.html has no S3 version"; assert d.get("Metadata", {}).get("deployment-sha256") == expected, "deployed index hash metadata does not match local build"; print("Verified index.html version " + d["VersionId"])' "$$head_response" "$$entry_sha"; \
	manifest_key="$(FRONTEND_DEPLOYMENT_PREFIX)/$$deployment_id-before.json"; \
	aws s3 cp "$$before_manifest" "s3://$(S3_BUCKET)/$$manifest_key" \
		--content-type "application/json" \
		--metadata "deployment-id=$$deployment_id,manifest-type=pre-deploy-current-versions" \
		--quiet \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)"; \
	echo "Rollback manifest: s3://$(S3_BUCKET)/$$manifest_key"; \
	invalidation_id="$$(aws cloudfront create-invalidation \
		--distribution-id $(CF_DIST_ID) \
		--paths "/*" \
		--profile "$(AWS_PROFILE)" \
		--query 'Invalidation.Id' \
		--output text)"; \
	echo "Waiting for CloudFront invalidation $$invalidation_id..."; \
	aws cloudfront wait invalidation-completed \
		--distribution-id $(CF_DIST_ID) \
		--id "$$invalidation_id" \
		--profile "$(AWS_PROFILE)"; \
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
	@if [ "$(ENV)" != "dev" ] && [ "$(ALLOW_NON_DEV_DEPLOY)" != "true" ]; then \
		echo "ERROR: this rollout path defaults to dev. Set ALLOW_NON_DEV_DEPLOY=true only after a separate environment review."; \
		exit 1; \
	fi
	@if [ "$(FRONTEND_DEV_MODE)" != "false" ]; then \
		echo "ERROR: AWS rollout requires FRONTEND_DEV_MODE=false."; \
		exit 1; \
	fi
	@set -eu; \
	case "$${MIDWAY_CLIENT_SECRET:-}" in \
		\** ) \
			echo "ERROR: MIDWAY_CLIENT_SECRET is a masked placeholder, not a deployable secret."; \
			exit 1 ;; \
		"" ) \
			if ! aws cloudformation describe-stacks \
				--stack-name "$(STACK_NAME)-$(ENV)" \
				--profile "$(AWS_PROFILE)" \
				--region "$(AWS_REGION)" \
				--query "Stacks[0].Parameters[?ParameterKey=='MidwayClientSecret'].ParameterKey | [0]" \
				--output text | rg -qx 'MidwayClientSecret'; then \
				echo "ERROR: MIDWAY_CLIENT_SECRET is required for a new stack; no existing stack parameter can be preserved."; \
				exit 1; \
			fi; \
			echo "Preserving the existing NoEcho Midway client secret." ;; \
		* ) echo "Using the explicitly injected Midway client secret." ;; \
	esac
	@if [ -z "$(strip $(ADMIN_ALIASES))" ]; then \
		echo "ERROR: ADMIN_ALIASES must identify every existing administrator for migration verification."; \
		exit 1; \
	fi
	@if [ "$(ADMIN_ALIAS_MIGRATION_ENABLED)" != "true" ] && \
	    [ "$(ADMIN_ALIAS_MIGRATION_ENABLED)" != "false" ]; then \
		echo "ERROR: ADMIN_ALIAS_MIGRATION_ENABLED must be true or false."; \
		exit 1; \
	fi
	@if [ "$(ENV)" != "dev" ]; then \
		if [ "$(FRONTEND_API_URL)" = "https://5kr7vlzkfj.execute-api.us-east-1.amazonaws.com/api/v1" ] || \
		   [ "$(FRONTEND_APP_URL)" = "https://d1wa5bvm23hhld.cloudfront.net" ] || \
		   [ "$(COGNITO_USER_POOL_ID)" = "us-east-1_oSEwvKdfd" ] || \
		   [ "$(COGNITO_CLIENT_ID)" = "6gbe6mt1il74sdqlq8boc60ld4" ] || \
		   [ "$(COGNITO_DOMAIN)" = "platform-advisor-dev-616627284001.auth.us-east-1.amazoncognito.com" ] || \
		   [ "$(COGNITO_IDENTITY_POOL_ID)" = "us-east-1:7494c292-da32-4ddf-b573-a4729ad4aeaf" ] || \
		   [ "$(MIDWAY_CLIENT_ID)" = "platform-advisor-dev" ] || \
		   [ "$(KNOWLEDGE_BASE_ID)" = "EDDM8YZDNJ" ] || \
		   [ "$(AGENTCORE_RUNTIME_ARN)" = "arn:aws:bedrock-agentcore:us-east-1:616627284001:runtime/PlatformAdvisorAgent_PlatformAdvisorAgent-3U71dVBprI" ] || \
		   [ "$(S3_BUCKET)" = "platform-advisor-frontend-dev-616627284001" ] || \
		   [ "$(CF_DIST_ID)" = "E33AR847I77OZS" ]; then \
			echo "ERROR: ENV=$(ENV) still points at the fixed dev estate; provide environment-specific values."; \
			exit 1; \
		fi; \
	fi
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

check-admin-migration:
	@set -eu; \
	stack_name="$(STACK_NAME)-$(ENV)"; \
	live_pool="$$(aws cloudformation describe-stacks \
		--stack-name "$$stack_name" \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)" \
		--query "Stacks[0].Outputs[?OutputKey=='UserPoolId'].OutputValue | [0]" \
		--output text)"; \
	if [ -z "$$live_pool" ] || [ "$$live_pool" = "None" ]; then \
		echo "ERROR: could not resolve UserPoolId from $$stack_name."; \
		exit 1; \
	fi; \
	if [ "$$live_pool" != "$(COGNITO_USER_POOL_ID)" ]; then \
		echo "ERROR: configured Cognito pool $(COGNITO_USER_POOL_ID) does not match $$stack_name output $$live_pool."; \
		exit 1; \
	fi; \
	admin_snapshot="$$(mktemp)"; \
	trap 'rm -f "$$admin_snapshot"' EXIT; \
	if [ "$(ADMIN_ALIAS_MIGRATION_ENABLED)" = "true" ]; then \
		if [ "$(ENV)" != "dev" ] || [ "$(ADMIN_ALIAS_MIGRATION_ACK)" != "dev-temporary-alias-fallback" ]; then \
			echo "ERROR: alias fallback is dev-only and requires ADMIN_ALIAS_MIGRATION_ACK=dev-temporary-alias-fallback."; \
			exit 1; \
		fi; \
		echo "WARNING: validating temporary dev alias fallback against enabled Cognito users."; \
		aws cognito-idp list-users \
			--user-pool-id "$$live_pool" \
			--profile "$(AWS_PROFILE)" \
			--region "$(AWS_REGION)" \
			--output json > "$$admin_snapshot"; \
		scope="enabled Cognito users"; \
	else \
		if ! aws cognito-idp list-users-in-group \
			--user-pool-id "$$live_pool" \
			--group-name "$(ADMIN_GROUP_NAME)" \
			--profile "$(AWS_PROFILE)" \
			--region "$(AWS_REGION)" \
			--output json > "$$admin_snapshot"; then \
			echo "ERROR: admin group is not available. First deploy once with the guarded dev migration fallback, enroll admins, then disable it."; \
			exit 1; \
		fi; \
		scope="the administrator-managed $(ADMIN_GROUP_NAME) group"; \
	fi; \
	ADMIN_ALIASES="$(ADMIN_ALIASES)" ADMIN_SCOPE="$$scope" python3 -c 'import json,os,sys; data=json.load(open(sys.argv[1])); expected={v.strip().lower() for v in os.environ["ADMIN_ALIASES"].split(",") if v.strip()}; users=data.get("Users", []); records=[(u, {str(u.get("Username", "")).lower()} | {str(a.get("Value", "")).lower() for a in u.get("Attributes", []) if a.get("Name") == "custom:amazon_alias"}) for u in users]; missing=sorted(a for a in expected if not any(a in identities for _,identities in records)); matched=[u for u,identities in records if identities & expected]; disabled=sorted(str(u.get("Username")) for u in matched if not u.get("Enabled", False)); unverified=sorted(str(u.get("Username")) for u in matched if u.get("UserStatus") not in ("CONFIRMED", "EXTERNAL_PROVIDER")); assert expected, "no admin identities were supplied"; assert not missing, "admins not verified in %s: %s" % (os.environ["ADMIN_SCOPE"], ", ".join(missing)); assert not disabled, "disabled admin users: %s" % ", ".join(disabled); assert not unverified, "unverified admin users: %s" % ", ".join(unverified); print("Verified %d administrator identity/identities in %s." % (len(expected), os.environ["ADMIN_SCOPE"]))' "$$admin_snapshot"

deploy-admin-migration-phase1:
	@$(MAKE) deploy \
		ENV=dev \
		ADMIN_ALIAS_MIGRATION_ENABLED=true \
		ADMIN_ALIAS_MIGRATION_ACK=dev-temporary-alias-fallback

deploy-admin-migration-phase2:
	@$(MAKE) deploy \
		ENV=dev \
		ADMIN_ALIAS_MIGRATION_ENABLED=false \
		ADMIN_ALIAS_MIGRATION_ACK=

configure-log-retention:
	@set -eu; \
	for log_group in \
		"/aws/lambda/platform-advisor-api-$(ENV)" \
		"/aws/lambda/platform-advisor-pre-token-$(ENV)"; do \
		existing="$$(aws logs describe-log-groups \
			--log-group-name-prefix "$$log_group" \
			--profile "$(AWS_PROFILE)" \
			--region "$(AWS_REGION)" \
			--query "logGroups[?logGroupName=='$$log_group'].logGroupName | [0]" \
			--output text)"; \
		if [ "$$existing" != "$$log_group" ]; then \
			aws logs create-log-group \
				--log-group-name "$$log_group" \
				--profile "$(AWS_PROFILE)" \
				--region "$(AWS_REGION)"; \
		fi; \
		aws logs put-retention-policy \
			--log-group-name "$$log_group" \
			--retention-in-days "$(LOG_RETENTION_DAYS)" \
			--profile "$(AWS_PROFILE)" \
			--region "$(AWS_REGION)"; \
		actual="$$(aws logs describe-log-groups \
			--log-group-name-prefix "$$log_group" \
			--profile "$(AWS_PROFILE)" \
			--region "$(AWS_REGION)" \
			--query "logGroups[?logGroupName=='$$log_group'].retentionInDays | [0]" \
			--output text)"; \
		if [ "$$actual" != "$(LOG_RETENTION_DAYS)" ]; then \
			echo "ERROR: $$log_group retention is $$actual, expected $(LOG_RETENTION_DAYS)."; \
			exit 1; \
		fi; \
		echo "Verified $$log_group retention: $$actual days."; \
	done

deploy: check-deploy-config check-admin-migration prepare-lambda
	@cd $(INFRA_DIR) && sam build --skip-pull-image && \
		sam validate --lint --template-file .aws-sam/build/template.yaml
	@set -eu; \
	midway_override=""; \
	if [ -n "$${MIDWAY_CLIENT_SECRET:-}" ]; then \
		midway_override="MidwayClientSecret=$${MIDWAY_CLIENT_SECRET}"; \
	fi; \
	cd $(INFRA_DIR) && \
		sam deploy \
		--stack-name $(STACK_NAME)-$(ENV) \
		--parameter-overrides \
			Env="$(ENV)" \
			AllowedOrigins="$(FRONTEND_APP_URL)" \
			DevMode="$(FRONTEND_DEV_MODE)" \
			AdminAlias="$(ADMIN_ALIASES)" \
			AdminGroupName="$(ADMIN_GROUP_NAME)" \
			AdminAliasMigrationEnabled="$(ADMIN_ALIAS_MIGRATION_ENABLED)" \
			MidwayClientId="$(MIDWAY_CLIENT_ID)" \
			$$midway_override \
			KnowledgeBaseId="$(KNOWLEDGE_BASE_ID)" \
			AgentCoreRuntimeArn="$(AGENTCORE_RUNTIME_ARN)" \
		--capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
		--resolve-s3 \
		--profile $(AWS_PROFILE) \
		--region $(AWS_REGION) \
		--confirm-changeset \
		--no-fail-on-empty-changeset && \
		$(MAKE) -C .. configure-log-retention \
			ENV="$(ENV)" \
			AWS_PROFILE="$(AWS_PROFILE)" \
			AWS_REGION="$(AWS_REGION)" \
			LOG_RETENTION_DAYS="$(LOG_RETENTION_DAYS)"

# Deploy the Strands agent pipeline to Amazon Bedrock AgentCore Runtime.
# Uses CodeZip (no Docker required).  Reads account/region from agentcore/aws-targets.json.
check-agentcore-cli:
	@if [ "$(ENV)" != "dev" ]; then \
		echo "ERROR: agentcore/aws-targets.json currently defines only the dev account/region; refusing ENV=$(ENV)."; \
		exit 1; \
	fi
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
	@set -eu; \
	state_file="$(AGENTCORE_DIR)/agentcore/.cli/deployed-state.json"; \
	if [ ! -f "$$state_file" ]; then \
		echo "ERROR: $$state_file is missing. Run make deploy-agentcore first."; \
		exit 1; \
	fi; \
	agent_arn="$$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("targets", {}).get("default", {}).get("resources", {}).get("runtimes", {}).get("PlatformAdvisorAgent", {}).get("runtimeArn", ""))' "$$state_file")"; \
	case "$$agent_arn" in \
		arn:*:bedrock-agentcore:*:*:runtime/*) ;; \
		*) echo "ERROR: deployed state does not contain a valid AgentCore Runtime ARN."; exit 1 ;; \
	esac; \
	runtime_id="$${agent_arn##*/}"; \
	live_runtime="$$(mktemp)"; \
	trap 'rm -f "$$live_runtime"' EXIT; \
	aws bedrock-agentcore-control get-agent-runtime \
		--agent-runtime-id "$$runtime_id" \
		--profile "$(AWS_PROFILE)" \
		--region "$(AWS_REGION)" \
		--output json > "$$live_runtime"; \
	python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); expected_arn=sys.argv[2]; expected_mode=sys.argv[3]; assert d.get("agentRuntimeArn") == expected_arn, "live AgentCore ARN does not match deployed state"; assert d.get("status") == "READY", "AgentCore runtime is not READY: %s" % d.get("status"); actual_mode=d.get("networkConfiguration", {}).get("networkMode"); assert actual_mode == expected_mode, "AgentCore network mode changed: %s" % actual_mode; print("Verified live READY runtime %s with %s network mode." % (expected_arn, actual_mode))' "$$live_runtime" "$$agent_arn" "$(AGENTCORE_NETWORK_MODE)"; \
	$(MAKE) deploy \
		AGENTCORE_RUNTIME_ARN="$$agent_arn" \
		ADMIN_ALIASES="$(ADMIN_ALIASES)" \
		ADMIN_GROUP_NAME="$(ADMIN_GROUP_NAME)" \
		ADMIN_ALIAS_MIGRATION_ENABLED="$(ADMIN_ALIAS_MIGRATION_ENABLED)" \
		ADMIN_ALIAS_MIGRATION_ACK="$(ADMIN_ALIAS_MIGRATION_ACK)"; \
	echo "Reviewed Lambda stack update completed with the live AgentCore Runtime ARN."

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	cd $(FRONTEND_DIR) && rm -rf .next node_modules
	find $(BACKEND_DIR) -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find $(BACKEND_DIR) -name "*.pyc" -delete 2>/dev/null || true
	cd $(INFRA_DIR) && rm -rf .aws-sam .lambda-src 2>/dev/null || true
