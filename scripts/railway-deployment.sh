#!/usr/bin/env bash
set -euo pipefail

: "${RAILWAY_TOKEN:?RAILWAY_TOKEN is required}"
: "${RAILWAY_SERVICE:?RAILWAY_SERVICE is required}"
: "${RAILWAY_ENVIRONMENT:?RAILWAY_ENVIRONMENT is required}"

graphql_url="https://backboard.railway.com/graphql/v2"

list_deployments() {
  railway deployment list \
    --service "${RAILWAY_SERVICE}" \
    --environment "${RAILWAY_ENVIRONMENT}" \
    --limit 20 \
    --json
}

deployment_field() {
  local deployments_json="$1"
  local deployment_id="${2:-}"
  local field="$3"

  DEPLOYMENTS_JSON="${deployments_json}" DEPLOYMENT_ID="${deployment_id}" FIELD="${field}" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["DEPLOYMENTS_JSON"])
if isinstance(payload, list):
    deployments = payload
elif isinstance(payload, dict):
    deployments = payload.get("deployments", payload.get("items", []))
    if isinstance(deployments, dict):
        deployments = deployments.get("edges", [])
else:
    deployments = []

normalized = []
for item in deployments:
    if isinstance(item, dict) and isinstance(item.get("node"), dict):
        normalized.append(item["node"])
    elif isinstance(item, dict):
        normalized.append(item)

deployment_id = os.environ["DEPLOYMENT_ID"]
if deployment_id:
    selected = next((item for item in normalized if item.get("id") == deployment_id), None)
else:
    selected = next(
        (
            item
            for item in normalized
            if str(item.get("status", "")).upper() in {"SUCCESS", "ACTIVE"}
        ),
        None,
    )

if selected is None:
    raise SystemExit("no matching Railway deployment found")

value = selected.get(os.environ["FIELD"])
if value is None:
    raise SystemExit(f"deployment has no {os.environ['FIELD']} field")
print(value)
PY
}

current_deployment() {
  deployment_field "$(list_deployments)" "" "id"
}

rollback_deployment() {
  local previous_deployment_id="$1"
  local payload
  local response
  local rollback_deployment_id

  payload="$(
    PREVIOUS_DEPLOYMENT_ID="${previous_deployment_id}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "query": (
        "mutation deploymentRollback($id: String!) { "
        "deploymentRollback(id: $id) { id } "
        "}"
    ),
    "variables": {"id": os.environ["PREVIOUS_DEPLOYMENT_ID"]},
}))
PY
  )"

  response="$(
    curl \
      --fail \
      --silent \
      --show-error \
      --request POST \
      --header "Content-Type: application/json" \
      --header "Project-Access-Token: ${RAILWAY_TOKEN}" \
      --data "${payload}" \
      "${graphql_url}"
  )"

  rollback_deployment_id="$(
    RAILWAY_RESPONSE="${response}" python3 - <<'PY'
import json
import os

payload = json.loads(os.environ["RAILWAY_RESPONSE"])
if payload.get("errors"):
    raise SystemExit(f"Railway rollback failed: {payload['errors']}")
deployment = payload.get("data", {}).get("deploymentRollback")
if not isinstance(deployment, dict) or not deployment.get("id"):
    raise SystemExit("Railway rollback response did not include a deployment ID")
print(deployment["id"])
PY
  )"

  echo "Rollback deployment ${rollback_deployment_id} started"
  for attempt in $(seq 1 60); do
    local deployments_json
    local status

    deployments_json="$(list_deployments)"
    status="$(deployment_field "${deployments_json}" "${rollback_deployment_id}" "status" 2>/dev/null || true)"
    status="$(printf '%s' "${status}" | tr '[:lower:]' '[:upper:]')"

    case "${status}" in
      SUCCESS|ACTIVE)
        echo "Rollback deployment is healthy"
        return 0
        ;;
      FAILED|CRASHED|REMOVED)
        echo "Rollback deployment ended with status ${status}"
        return 1
        ;;
      *)
        echo "Waiting for rollback deployment... (${attempt}/60, status=${status:-unknown})"
        sleep 5
        ;;
    esac
  done

  echo "Rollback deployment did not become healthy in time"
  return 1
}

case "${1:-}" in
  current)
    current_deployment
    ;;
  rollback)
    : "${2:?previous deployment ID is required}"
    rollback_deployment "$2"
    ;;
  *)
    echo "usage: $0 current | rollback <deployment-id>" >&2
    exit 2
    ;;
esac
