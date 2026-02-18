#!/usr/bin/env bash
set -euo pipefail

ACME=/root/.acme.sh/acme.sh
DOMAIN=petsy.company

mkdir -p /etc/nginx/ssl/petsy_wildcard

# Install cert (will exist after successful DNS-01 renewal)
$ACME --install-cert -d "$DOMAIN" --ecc \
  --fullchain-file /etc/nginx/ssl/petsy_wildcard/fullchain.pem \
  --key-file /etc/nginx/ssl/petsy_wildcard/privkey.pem \
  --reloadcmd "systemctl reload nginx"

# Enable nginx wildcard site if not enabled
ln -sf /etc/nginx/sites-available/petsy-wildcard /etc/nginx/sites-enabled/petsy-wildcard
nginx -t
systemctl reload nginx

echo "Wildcard cert installed + nginx wildcard vhost enabled."
