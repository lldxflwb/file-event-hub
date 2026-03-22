#!/bin/bash
# file-event-hub PostToolUse hook
# Captures Edit/Write events and POSTs to the event hub server

# Redirect all stderr to /dev/null for truly silent failure
exec 2>/dev/null

set +e

SERVER_URL="${FILE_EVENT_HUB_URL:-http://localhost:9120}"

input=$(cat)

tool_name=$(jq -r '.tool_name // empty' <<< "$input")

case "$tool_name" in
  Edit|Write) ;;
  *) exit 0 ;;
esac

file_path=$(jq -r '.tool_input.file_path // empty' <<< "$input")
[ -z "$file_path" ] && exit 0

timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.000Z")

if [ "$tool_name" = "Edit" ]; then
  # Read current file content post-modification (Edit tool only provides the diff)
  new_content=""
  if [ -f "$file_path" ]; then
    new_content=$(cat "$file_path" || true)
  fi

  event_json=$(jq -n \
    --arg fp "$file_path" \
    --arg tool "$tool_name" \
    --arg ts "$timestamp" \
    --arg nc "$new_content" \
    --argjson inp "$input" \
    '{
      file_path: $fp,
      tool: $tool,
      timestamp: $ts,
      new_content: $nc,
      old_text: ($inp.tool_input.old_string // ""),
      new_text: ($inp.tool_input.new_string // "")
    }')
else
  # For Write, tool_input.content already has the full file content
  event_json=$(jq -n \
    --arg fp "$file_path" \
    --arg tool "$tool_name" \
    --arg ts "$timestamp" \
    --argjson inp "$input" \
    '{
      file_path: $fp,
      tool: $tool,
      timestamp: $ts,
      new_content: ($inp.tool_input.content // "")
    }')
fi

# POST in background to avoid blocking Claude Code
curl -s -X POST "${SERVER_URL}/api/events" \
  -H "Content-Type: application/json" \
  -d "$event_json" \
  --connect-timeout 2 \
  --max-time 5 \
  > /dev/null &

exit 0
