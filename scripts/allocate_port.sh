#!/usr/bin/env bash
set -euo pipefail
REGISTRY=${REGISTRY:-/srv/ai-software-factory/projects/registry.json}
mkdir -p "$(dirname "$REGISTRY")"
[ -f "$REGISTRY" ] || echo '{}' > "$REGISTRY"
python3 - <<'PY'
import json
reg_path='/srv/ai-software-factory/projects/registry.json'
with open(reg_path,'r') as f:
    reg=json.load(f) if f.read().strip() else {}
used={int(v.get('port')) for v in reg.values() if isinstance(v,dict) and v.get('port')}
for p in range(12000,13000):
    if p not in used:
        print(p)
        raise SystemExit(0)
raise SystemExit('No free ports in 12000-12999')
PY
