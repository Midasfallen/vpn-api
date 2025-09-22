#!/bin/bash
set -e
cat > /tmp/login.json <<'JSON'
{"email":"zcxvbnm@m.com","password":"qxgbjuru"}
JSON

curl -sS -X POST http://127.0.0.1:8000/auth/login -H 'Content-Type: application/json' --data-binary @/tmp/login.json -o /tmp/token.json -w 'http_code:%{http_code}\n'
cat /tmp/token.json || true
TOKEN=$(python3 - <<'PY'
import json
obj=json.load(open('/tmp/token.json'))
print(obj.get('access_token',''))
PY
)
echo "TOKEN:$TOKEN"
if [ -z "$TOKEN" ]; then echo 'no token, abort'; exit 2; fi
cat > /tmp/peer.json <<'JSON'
{"name":"test-wg-easy-go","allowed_ips":"10.99.99.10/32","dns":"1.1.1.1","description":"test created via wg-easy integration","wg_public_key":"somepubkey","wg_ip":"10.99.99.10"}
JSON

curl -sS -X POST http://127.0.0.1:8000/vpn_peers/ -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" --data-binary @/tmp/peer.json -o /tmp/peer_resp.json -w 'http_code:%{http_code}\n'
cat /tmp/peer_resp.json || true

docker compose exec -T db psql -U postgres -d vpn -c "SELECT id,name,wg_client_id,created_at FROM vpn_peers ORDER BY id DESC LIMIT 10;"

curl -sS http://62.84.98.109:8588/clients | head -n 200 || true
