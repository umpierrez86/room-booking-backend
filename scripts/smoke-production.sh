#!/usr/bin/env bash
set -euo pipefail

: "${PRODUCTION_URL:?PRODUCTION_URL is required}"
: "${SMOKE_USERNAME:?SMOKE_USERNAME is required}"
: "${SMOKE_PASSWORD:?SMOKE_PASSWORD is required}"

base_url="${PRODUCTION_URL%/}"
request_timeout=10

retry_get() {
  curl \
    --fail \
    --silent \
    --show-error \
    --retry 12 \
    --retry-all-errors \
    --retry-delay 5 \
    --max-time "${request_timeout}" \
    "$@"
}

echo "Checking API health"
health_response="$(retry_get "${base_url}/health")"
HEALTH_RESPONSE="${health_response}" python - <<'PY'
import json
import os

payload = json.loads(os.environ["HEALTH_RESPONSE"])
if payload.get("status") != "ok":
    raise SystemExit("health response did not report status=ok")
PY

echo "Checking protected routes reject anonymous requests"
anonymous_status="$(
  curl \
    --silent \
    --show-error \
    --output /dev/null \
    --write-out "%{http_code}" \
    --max-time "${request_timeout}" \
    "${base_url}/rooms"
)"
if [[ "${anonymous_status}" != "401" ]]; then
  echo "expected /rooms to return 401 without a token, got ${anonymous_status}"
  exit 1
fi

echo "Authenticating smoke-test user"
login_payload="$(
  SMOKE_USERNAME="${SMOKE_USERNAME}" SMOKE_PASSWORD="${SMOKE_PASSWORD}" python - <<'PY'
import json
import os

print(json.dumps({
    "username": os.environ["SMOKE_USERNAME"],
    "password": os.environ["SMOKE_PASSWORD"],
}))
PY
)"
login_response="$(
  curl \
    --fail \
    --silent \
    --show-error \
    --max-time "${request_timeout}" \
    --header "Content-Type: application/json" \
    --data "${login_payload}" \
    "${base_url}/auth/login"
)"
access_token="$(
  LOGIN_RESPONSE="${login_response}" python - <<'PY'
import json
import os

token = json.loads(os.environ["LOGIN_RESPONSE"]).get("access_token")
if not token:
    raise SystemExit("login response did not include an access token")
print(token)
PY
)"

echo "Checking authenticated room catalog"
rooms_response="$(
  retry_get \
    --header "Authorization: Bearer ${access_token}" \
    "${base_url}/rooms"
)"
ROOMS_RESPONSE="${rooms_response}" python - <<'PY'
import json
import os

rooms = json.loads(os.environ["ROOMS_RESPONSE"])
if not isinstance(rooms, list) or not rooms:
    raise SystemExit("room catalog is empty or malformed")
for room in rooms:
    if not isinstance(room.get("code"), str) or not isinstance(room.get("capacity"), int):
        raise SystemExit("room catalog contains malformed entries")
PY

echo "Checking authenticated schedule"
smoke_date="$(date -u +%F)"
schedule_response="$(
  retry_get \
    --header "Authorization: Bearer ${access_token}" \
    "${base_url}/schedule?date=${smoke_date}"
)"
SCHEDULE_RESPONSE="${schedule_response}" SMOKE_DATE="${smoke_date}" python - <<'PY'
import json
import os

schedule = json.loads(os.environ["SCHEDULE_RESPONSE"])
if schedule.get("date") != os.environ["SMOKE_DATE"]:
    raise SystemExit("schedule returned an unexpected date")
if not isinstance(schedule.get("rooms"), list) or not schedule["rooms"]:
    raise SystemExit("schedule contains no rooms")
PY

echo "Backend production smoke test passed"
