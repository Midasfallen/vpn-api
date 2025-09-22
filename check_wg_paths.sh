#!/bin/bash
set -e
echo 'GET /clients'
curl -sS -i http://62.84.98.109:8588/clients || true

echo '\nGET /api/clients'
curl -sS -i http://62.84.98.109:8588/api/clients || true

echo '\nGET /api/v1/clients'
curl -sS -i http://62.84.98.109:8588/api/v1/clients || true

echo '\nGET /api/wireguard/clients'
curl -sS -i http://62.84.98.109:8588/api/wireguard/clients || true

echo '\nGET /api/wireguard/client/1/configuration (example)'
curl -sS -i http://62.84.98.109:8588/api/wireguard/client/1/configuration || true
