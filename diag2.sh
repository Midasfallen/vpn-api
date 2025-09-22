#!/bin/bash
set -e
cd /srv/vpn-api || exit 1
echo '--- .env.production ---'
cat .env.production || true

echo '--- WG env in web container ---'
docker compose exec -T web /bin/sh -lc 'printenv | grep -i WG || true'

echo '--- test possible wg-easy endpoints from server (no write operations) ---'
WGURL=$(grep -E '^WG_EASY_URL=' .env.production | cut -d'=' -f2- | tr -d '"')
echo 'WGURL='"$WGURL"

for p in "" "/clients" "/api/clients" "/api/v1/clients" "/api" "/status" "/api/status"; do
  url="$WGURL$p"
  echo "--- GET $url ---"
  curl -sS -i -m 10 "$url" || echo 'curl-failed'
done

echo '--- try GET via container (to ensure same network) ---'
docker compose exec -T web /bin/sh -lc "python3 - <<'PY'
import os,subprocess
wg = os.getenv('WG_EASY_URL','')
print('WG_EASY_URL env in container:', wg)
if wg:
    import requests
    try:
        print('container GET', requests.get(wg, timeout=5).status_code)
    except Exception as e:
        print('container curl error', e)
PY"
