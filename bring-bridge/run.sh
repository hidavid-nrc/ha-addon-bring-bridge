#!/usr/bin/env bash
set -euo pipefail

# Load options from Home Assistant
if [ -f /data/options.json ]; then
  export API_KEY=$(jq -r '.api_key // empty' /data/options.json)
  export BRING_EMAIL=$(jq -r '.bring_email' /data/options.json)
  export BRING_PASSWORD=$(jq -r '.bring_password' /data/options.json)
  export BRING_LIST_NAME=$(jq -r '.bring_list_name // empty' /data/options.json)
fi

# Start the API
exec uvicorn main:app --host 0.0.0.0 --port 8000

