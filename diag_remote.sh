#!/bin/bash
set -e
cd /srv/vpn-api || exit 1
echo '--- docker compose ps ---'
docker compose ps

echo '--- docker compose logs --tail 400 web ---'
docker compose logs --no-color --tail 400 web || true

echo '--- try import wg_easy_api inside web container ---'
docker compose exec -T web /bin/sh -lc "python3 - <<'PY'
import importlib,traceback
try:
    mod = importlib.import_module('wg_easy_api')
    print('wg_easy_api OK', getattr(mod,'__version__','no-version'))
except Exception as e:
    print('IMPORT-ERROR:', type(e), e)
    traceback.print_exc()
PY"

echo '--- curl local root verbose ---'
curl -v http://127.0.0.1:8000/ || true

echo '--- curl wg-easy clients verbose ---'
curl -v http://62.84.98.109:8588/clients || true
