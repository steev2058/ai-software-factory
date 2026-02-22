#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${1:-}"
if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <PROJECT_ID>" >&2
  exit 1
fi
ROOT=/srv/ai-software-factory
PROJECT_DIR="$ROOT/projects/$PROJECT_ID"
TEMPLATE="$ROOT/templates/micro-saas-template"

mkdir -p "$PROJECT_DIR"
cp -R "$TEMPLATE"/. "$PROJECT_DIR"/

# inject placeholder helper for tool logic (called by /api/use in server.js future extension)
cat > "$PROJECT_DIR/tool_logic.js" <<'JS'
module.exports = async function toolLogic({ prompt }) {
  return `Tool placeholder response for: ${prompt}`;
};
JS

# ensure env skeleton exists
cat > "$PROJECT_DIR/.env" <<ENV
PORT=3000
ADMIN_TOKEN=
OPENROUTER_API_KEY=
OPENROUTER_MODEL=openai/gpt-4o-mini
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=
PAYPAL_CLIENT_SECRET=
PAYPAL_WEBHOOK_ID=
ENV

# ensure /health contract present
if ! grep -q "app.get('/health'" "$PROJECT_DIR/server.js"; then
  echo "health endpoint missing" >&2
  exit 2
fi

echo "Monetized template prepared at $PROJECT_DIR"
