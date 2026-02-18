#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DASHBOARD_USER:-}" || -z "${DASHBOARD_PASS:-}" ]]; then
  echo "ERROR: DASHBOARD_USER and DASHBOARD_PASS must be set"
  exit 1
fi

htpasswd -bc /etc/nginx/.htpasswd "$DASHBOARD_USER" "$DASHBOARD_PASS" >/dev/null 2>&1

exec nginx -g 'daemon off;'
