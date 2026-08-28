#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FRONTEND_DIR="$ROOT_DIR/frontend"
REPORT_DIR="$ROOT_DIR/.reports/deployment-review"
STRICT=0
DEPLOYED_URL=""
API_URL=""

usage() {
  cat <<'EOF'
Usage:
  ./scripts/deployment-review.sh [--strict] [--deployed-url URL] [--api-url URL] [--report-dir DIR]

Examples:
  ./scripts/deployment-review.sh
  ./scripts/deployment-review.sh --deployed-url https://example.cloudfront.net
  ./scripts/deployment-review.sh --strict --deployed-url https://example.cloudfront.net --api-url https://api.example.com
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --strict)
      STRICT=1
      shift
      ;;
    --deployed-url)
      DEPLOYED_URL="${2:-}"
      shift 2
      ;;
    --api-url)
      API_URL="${2:-}"
      shift 2
      ;;
    --report-dir)
      REPORT_DIR="${2:-}"
      shift 2
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")-$$"
RUN_DIR="$REPORT_DIR/$TIMESTAMP"
LOG_DIR="$RUN_DIR/logs"
SUMMARY_FILE="$RUN_DIR/summary.md"
LATEST_FILE="$REPORT_DIR/latest.md"

mkdir -p "$LOG_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

CHECK_NAMES=()
CHECK_STATUS=()
CHECK_SEVERITY=()
CHECK_DETAIL=()
CHECK_LOGS=()

add_check() {
  CHECK_NAMES+=("$1")
  CHECK_STATUS+=("$2")
  CHECK_SEVERITY+=("$3")
  CHECK_DETAIL+=("$4")
  CHECK_LOGS+=("$5")
}

run_check() {
  local key="$1"
  local label="$2"
  local severity="$3"
  shift 3

  local log_file="$LOG_DIR/${key}.log"
  local cmd=("$@")

  {
    echo "+ ${cmd[*]}"
    echo ""
    "${cmd[@]}"
  } >"$log_file" 2>&1
  local exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    add_check "$label" "passed" "$severity" "Command completed successfully." "$log_file"
  else
    add_check "$label" "failed" "$severity" "Command exited with status $exit_code." "$log_file"
  fi
}

skip_check() {
  local key="$1"
  local label="$2"
  local severity="$3"
  local reason="$4"
  local log_file="$LOG_DIR/${key}.log"

  printf '%s\n' "$reason" >"$log_file"
  add_check "$label" "skipped" "$severity" "$reason" "$log_file"
}

has_pytest() {
  "$PYTHON_BIN" -m pytest --version >/dev/null 2>&1
}

has_frontend_deps() {
  [[ -d "$FRONTEND_DIR/node_modules" ]]
}

run_curl_check() {
  local key="$1"
  local label="$2"
  local severity="$3"
  local url="$4"
  local log_file="$LOG_DIR/${key}.log"

  {
    echo "+ curl -fsSIL $url"
    echo ""
    curl -fsSIL "$url"
  } >"$log_file" 2>&1
  local exit_code=$?

  if [[ $exit_code -eq 0 ]]; then
    add_check "$label" "passed" "$severity" "Endpoint responded successfully." "$log_file"
  else
    add_check "$label" "failed" "$severity" "Endpoint probe failed with status $exit_code." "$log_file"
  fi
}

if has_frontend_deps; then
  run_check "frontend-build" "Frontend production build" "required" \
    bash -lc "cd \"$FRONTEND_DIR\" && npm run build"
  run_check "frontend-review-audit" "Frontend seeded review audit" "required" \
    bash -lc "cd \"$FRONTEND_DIR\" && npm run review:audit"
  if [[ $STRICT -eq 1 ]]; then
    run_check "frontend-review-audit-strict" "Frontend strict review audit" "required" \
      bash -lc "cd \"$FRONTEND_DIR\" && npm run review:audit:strict"
  fi
else
  skip_check "frontend-build" "Frontend production build" "required" "Skipped: frontend/node_modules is missing."
  skip_check "frontend-review-audit" "Frontend seeded review audit" "required" "Skipped: frontend/node_modules is missing."
fi

if has_pytest; then
  run_check "backend-pytest" "Backend API tests" "required" \
    "$PYTHON_BIN" -m pytest backend/tests -q
  run_check "agent-pytest" "Agent runtime tests" "required" \
    "$PYTHON_BIN" -m pytest agent/app/CodingAgentRuntime/tests -q
else
  skip_check "backend-pytest" "Backend API tests" "required" "Skipped: pytest is not installed for $PYTHON_BIN."
  skip_check "agent-pytest" "Agent runtime tests" "required" "Skipped: pytest is not installed for $PYTHON_BIN."
fi

if [[ -n "$DEPLOYED_URL" ]]; then
  run_curl_check "deployed-home" "Deployed frontend root" "required" "$DEPLOYED_URL"
  run_curl_check "deployed-review" "Deployed review route" "advisory" "${DEPLOYED_URL%/}/review"
fi

if [[ -n "$API_URL" ]]; then
  run_curl_check "api-health" "Backend health endpoint" "required" "${API_URL%/}/health"
fi

required_failures=0
required_skips=0
advisory_failures=0
passed_count=0
skipped_count=0

for i in "${!CHECK_NAMES[@]}"; do
  status="${CHECK_STATUS[$i]}"
  severity="${CHECK_SEVERITY[$i]}"
  if [[ "$status" == "passed" ]]; then
    passed_count=$((passed_count + 1))
  elif [[ "$status" == "skipped" ]]; then
    skipped_count=$((skipped_count + 1))
    if [[ "$severity" == "required" ]]; then
      required_skips=$((required_skips + 1))
    fi
  elif [[ "$severity" == "required" ]]; then
    required_failures=$((required_failures + 1))
  else
    advisory_failures=$((advisory_failures + 1))
  fi
done

overall_status="passed"
if [[ $required_failures -gt 0 ]]; then
  overall_status="failed"
elif [[ $required_skips -gt 0 || $advisory_failures -gt 0 ]]; then
  overall_status="attention"
fi

{
  echo "# Deployment Review"
  echo ""
  echo "- Timestamp (UTC): \`$TIMESTAMP\`"
  echo "- Overall status: \`$overall_status\`"
  echo "- Passed: \`$passed_count\`"
  echo "- Skipped: \`$skipped_count\`"
  echo "- Required failures: \`$required_failures\`"
  echo "- Required skips: \`$required_skips\`"
  echo "- Advisory failures: \`$advisory_failures\`"
  if [[ -n "$DEPLOYED_URL" ]]; then
    echo "- Deployed URL: \`$DEPLOYED_URL\`"
  fi
  if [[ -n "$API_URL" ]]; then
    echo "- API URL: \`$API_URL\`"
  fi
  echo ""
  echo "## Checks"
  echo ""

  for i in "${!CHECK_NAMES[@]}"; do
    name="${CHECK_NAMES[$i]}"
    status="${CHECK_STATUS[$i]}"
    severity="${CHECK_SEVERITY[$i]}"
    detail="${CHECK_DETAIL[$i]}"
    log_path="${CHECK_LOGS[$i]}"
    echo "- **$name**: \`$status\` ($severity)"
    echo "  Detail: $detail"
    echo "  Log: \`$log_path\`"
  done

  echo ""
  echo "## Review Notes"
  echo ""
  if [[ $required_failures -eq 0 && $advisory_failures -eq 0 ]]; then
    echo "- No failing checks in this run."
  fi
  if [[ $required_failures -gt 0 ]]; then
    echo "- Resolve required failures before treating the deployment as verified."
  fi
  if [[ $required_skips -gt 0 ]]; then
    echo "- Required checks were skipped, so this run did not produce full verification coverage."
  fi
  if [[ $advisory_failures -gt 0 ]]; then
    echo "- Advisory failures did not block the run, but they should be reviewed."
  fi
  if [[ $skipped_count -gt 0 ]]; then
    echo "- Some checks were skipped because the local environment is missing dependencies or a target URL was not supplied."
  fi
} >"$SUMMARY_FILE"

cp "$SUMMARY_FILE" "$LATEST_FILE"

echo "Deployment review written to:"
echo "  $SUMMARY_FILE"
echo ""
sed -n '1,120p' "$SUMMARY_FILE"

if [[ $required_failures -gt 0 || ( $STRICT -eq 1 && $required_skips -gt 0 ) ]]; then
  exit 1
fi

exit 0
