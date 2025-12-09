#!/usr/bin/env bash
# server_inspect.sh
# Usage (local machine): ssh root@146.103.99.70 'bash -s' < ./scripts/server_inspect.sh
# This script runs read-only inspections on the deploy host and writes results to /tmp/server_inspect_<timestamp>.tar.gz
set -euo pipefail
TS=$(date -u +%Y%m%dT%H%M%SZ)
OUTDIR="/tmp/server_inspect_$TS"
mkdir -p "$OUTDIR"

echo "Collecting system info..." > "$OUTDIR/summary.txt"
uname -a >> "$OUTDIR/summary.txt" 2>&1 || true
cat /etc/os-release >> "$OUTDIR/summary.txt" 2>&1 || true

# Find compose file and deployment path heuristics
echo "Looking for docker compose files in /srv /opt /home /root" >> "$OUTDIR/summary.txt"
for p in /srv /opt /home /root; do
  if [ -d "$p" ]; then
    find "$p" -maxdepth 3 -type f -name "docker-compose*.yml" -o -name "docker-compose*.yaml" -print >> "$OUTDIR/summary.txt" 2>/dev/null || true
  fi
done

# Docker info
if command -v docker >/dev/null 2>&1; then
  docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}' > "$OUTDIR/docker_ps.txt" 2>&1 || true
  docker info > "$OUTDIR/docker_info.txt" 2>&1 || true
else
  echo "docker command not found" > "$OUTDIR/docker_ps.txt"
fi

# Docker-compose ps and logs (try find a compose file)
COMPOSE_FILE=$(find / -maxdepth 3 -type f -name "docker-compose.yml" -o -name "docker-compose.yaml" -print -quit 2>/dev/null || true)
if [ -n "$COMPOSE_FILE" ]; then
  echo "Found compose file: $COMPOSE_FILE" >> "$OUTDIR/summary.txt"
  COMPOSE_DIR=$(dirname "$COMPOSE_FILE")
  echo "Running docker compose ps in $COMPOSE_DIR" >> "$OUTDIR/summary.txt"
  (cd "$COMPOSE_DIR" && docker compose ps > "$OUTDIR/compose_ps.txt" 2>&1) || true
  # attempt to collect logs for likely service names
  (cd "$COMPOSE_DIR" && docker compose logs --tail=200 web > "$OUTDIR/logs_web.txt" 2>&1) || true
  (cd "$COMPOSE_DIR" && docker compose logs --tail=200 wg-easy > "$OUTDIR/logs_wg_easy.txt" 2>&1) || true
  (cd "$COMPOSE_DIR" && docker compose logs --tail=200 db > "$OUTDIR/logs_db.txt" 2>&1) || true
  (cd "$COMPOSE_DIR" && docker compose logs --tail=200 vpn-api > "$OUTDIR/logs_vpn_api.txt" 2>&1) || true
else
  echo "No docker-compose.yml found under / (searched depth 3)" >> "$OUTDIR/summary.txt"
fi

# Attempt to dump .env.production if present near compose file or in current dir
for f in "$COMPOSE_DIR/.env.production" "/opt/.env.production" "/srv/.env.production" "/root/.env.production"; do
  if [ -f "$f" ]; then
    echo "Found $f" >> "$OUTDIR/summary.txt"
    sed -n '1,200p' "$f" > "$OUTDIR/env_production.txt" 2>&1 || true
    break
  fi
done

# Try to query DB for vpn_peers if we can find a postgres container
DB_CONTAINER=$(docker ps --format '{{.Names}}' | grep -E 'postgres|db|postgresql' | head -n1 || true)
if [ -n "$DB_CONTAINER" ]; then
  echo "Found DB container: $DB_CONTAINER" >> "$OUTDIR/summary.txt"
  # If psql exists in container, try to pull last 20 peers
  docker exec -it "$DB_CONTAINER" psql -c "\dt" >/dev/null 2>&1 || PSQL_OK=0 || true
  if docker exec "$DB_CONTAINER" psql -U postgres -c "SELECT 1;" >/dev/null 2>&1; then
    docker exec "$DB_CONTAINER" psql -U postgres -c "SELECT id, user_id, wg_public_key, wg_ip, active, created_at FROM vpn_peers ORDER BY created_at DESC LIMIT 20;" > "$OUTDIR/vpn_peers_head.txt" 2>&1 || true
  else
    echo "psql invocation failed or unknown credentials; skipping DB query" > "$OUTDIR/vpn_peers_head.txt"
  fi
else
  echo "No obvious Postgres container found (by name)" > "$OUTDIR/vpn_peers_head.txt"
fi

# Package output
tar -czf "/tmp/server_inspect_$TS.tar.gz" -C /tmp "server_inspect_$TS" || true
echo "Wrote archive: /tmp/server_inspect_$TS.tar.gz"
ls -lh "/tmp/server_inspect_$TS.tar.gz" || true
echo "Done"
