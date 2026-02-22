#!/usr/bin/env bash
set -euo pipefail
PROJECT_ID="${1:-}"
if [ -z "$PROJECT_ID" ]; then
  echo "Usage: $0 <PROJECT_ID>" >&2
  exit 1
fi
ROOT=/srv/ai-software-factory
PROJECT_DIR="$ROOT/projects/$PROJECT_ID"
REGISTRY="$ROOT/projects/registry.json"
DOMAIN="${PROJECT_ID}.petsy.company"
NGINX_AVAIL="/etc/nginx/sites-available/${DOMAIN}.conf"
NGINX_ENABLED="/etc/nginx/sites-enabled/${DOMAIN}.conf"
CONTAINER="saas_${PROJECT_ID}"

if [ ! -f "$PROJECT_DIR/package.json" ]; then
  echo "Project missing package.json: $PROJECT_DIR" >&2
  exit 2
fi

mkdir -p "$(dirname "$REGISTRY")"
[ -f "$REGISTRY" ] || echo '{}' > "$REGISTRY"

PORT=$(python3 - <<PY
import json
reg_path='$REGISTRY'
pid='$PROJECT_ID'
with open(reg_path,'r') as f:
    txt=f.read().strip()
reg=json.loads(txt) if txt else {}
if pid in reg and isinstance(reg[pid],dict) and reg[pid].get('port'):
    print(reg[pid]['port'])
    raise SystemExit(0)
used={int(v.get('port')) for v in reg.values() if isinstance(v,dict) and v.get('port')}
for p in range(12000,13000):
    if p not in used:
        print(p)
        raise SystemExit(0)
raise SystemExit('No free ports')
PY
)

# compose env from global + project
GLOBAL_ENV="$ROOT/.env"
PROJECT_ENV="$PROJECT_DIR/.env"
[ -f "$PROJECT_ENV" ] || touch "$PROJECT_ENV"
if [ -f "$GLOBAL_ENV" ]; then
  awk -F= '/^(ADMIN_TOKEN|OPENROUTER_API_KEY|OPENROUTER_MODEL|PAYPAL_MODE|PAYPAL_CLIENT_ID)=/{print}' "$GLOBAL_ENV" >> "$PROJECT_ENV" || true
fi
sed -i "/^PORT=/d" "$PROJECT_ENV"
echo "PORT=3000" >> "$PROJECT_ENV"

# build + run
cd "$PROJECT_DIR"
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker build -t "$CONTAINER:latest" .
docker run -d --name "$CONTAINER" --restart unless-stopped --env-file "$PROJECT_ENV" -p "127.0.0.1:${PORT}:3000" "$CONTAINER:latest"

# nginx
cat > "$NGINX_AVAIL" <<CONF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
CONF
ln -sf "$NGINX_AVAIL" "$NGINX_ENABLED"
nginx -t
systemctl reload nginx

# certbot (best effort)
if command -v certbot >/dev/null 2>&1; then
  certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos -m admin@petsy.company --redirect || true
fi

# update registry
python3 - <<PY
import json, datetime
reg_path='$REGISTRY'
pid='$PROJECT_ID'
port=int('$PORT')
domain='$DOMAIN'
url=f'https://{domain}'
container='$CONTAINER'
with open(reg_path,'r') as f:
    txt=f.read().strip()
reg=json.loads(txt) if txt else {}
reg[pid]={
  'port':port,
  'domain':domain,
  'url':url,
  'container':container,
  'updated_at':datetime.datetime.utcnow().isoformat()+'Z'
}
with open(reg_path,'w') as f:
    json.dump(reg,f,indent=2)
PY

echo "Deployed: https://${DOMAIN} -> 127.0.0.1:${PORT}"
