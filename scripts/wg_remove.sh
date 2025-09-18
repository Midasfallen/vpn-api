#!/usr/bin/env bash
# Remove a peer from the local WireGuard interface.
# Usage: wg_remove.sh <iface> <peer_public_key>
set -euo pipefail
iface="$1"
peer_pub="$2"

if [ -z "${peer_pub}" ]; then
  echo "missing public key" >&2
  exit 2
fi

if ! ip link show "$iface" >/dev/null 2>&1; then
  echo "wireguard interface $iface not found" >&2
  exit 3
fi

if ! wg show "$iface" peers | grep -qx "$peer_pub"; then
  echo "peer not present" >&2
  exit 0
fi

wg set "$iface" peer "$peer_pub" remove
echo "peer removed"
