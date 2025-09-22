#!/bin/bash
set -e
# login
cat > /tmp/login.json <<'JSON'
{"email":"zcxvbnm@m.com","password":"qxgbjuru"}
JSON
curl -sS -X POST http://127.0.0.1:8000/auth/login -H 'Content-Type: application/json' --data-binary @/tmp/login.json -o /tmp/token.json -w 'http_code:%{http_code}\n'
cat /tmp/token.json || true
TOKEN=$(python3 - <<'PY'
import json
try:
    obj=json.load(open('/tmp/token.json'))
    print(obj.get('access_token',''))
except Exception:
    print('')
PY
)
echo "TOKEN:$TOKEN"
if [ -z "$TOKEN" ]; then echo 'no token, abort'; exit 2; fi
# get current user
curl -sS -X GET http://127.0.0.1:8000/me -H "Authorization: Bearer $TOKEN" -o /tmp/me.json -w 'http_code:%{http_code}\n'
cat /tmp/me.json || true
USER_ID=$(python3 - <<'PY'
import json
try:
    obj=json.load(open('/tmp/me.json'))
    print(obj.get('id',''))
except Exception:
    print('')
PY
)
echo "USER_ID:$USER_ID"
if [ -z "$USER_ID" ]; then echo 'no user id, abort'; exit 3; fi
# create peer with user_id
cat > /tmp/peer.json <<JSON
{"user_id": %s, "name":"test-wg-easy-go","allowed_ips":"10.99.99.10/32","dns":"1.1.1.1","description":"test created via wg-easy integration","wg_public_key":"somepubkey-%s","wg_ip":"10.99.99.10"}
JSON

# substitute USER_ID into file
python3 - <<'PY'
import io,sys
uid = sys.argv[1]
with open('/tmp/peer.json') as f:
    s = f.read()
print(s %% (uid, uid))
PY "$USER_ID" > /tmp/peer.json

echo '--- POST /vpn_peers/ ---'
curl -sS -X POST http://127.0.0.1:8000/vpn_peers/ -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" --data-binary @/tmp/peer.json -o /tmp/peer_resp.json -w 'http_code:%{http_code}\n'
cat /tmp/peer_resp.json || true

echo '--- db vpn_peers (last 10) ---'
docker compose exec -T db psql -U postgres -d vpn -c "SELECT id,name,user_id,wg_client_id,created_at FROM vpn_peers ORDER BY id DESC LIMIT 10;"

echo '--- wg-easy clients ---'
curl -sS http://62.84.98.109:8588/clients | head -n 200 || true
