#!/usr/bin/env bash
# Apply a peer to the local WireGuard interface.
# Usage: wg_apply.sh <iface> <peer_public_key> <allowed_ips>
set -euo pipefail
iface="$1"
peer_pub="$2"
allowed_ips="$3"

if [ -z "${peer_pub}" ]; then
  echo "missing public key" >&2
  exit 2
fi

# Ensure interface exists
if ! ip link show "$iface" >/dev/null 2>&1; then
  echo "wireguard interface $iface not found" >&2
  exit 3
fi

# Check if peer already exists
if wg show "$iface" peers | grep -qx "$peer_pub"; then
  echo "peer already present" >&2
  exit 0
fi

# Add peer
if [ -z "$allowed_ips" ]; then
  allowed_ips="0.0.0.0/0"
fi

wg set "$iface" peer "$peer_pub" allowed-ips "$allowed_ips"
echo "peer added"
