#!/usr/bin/env bash
# Generate WireGuard keypair and print public key and private key path
# Usage: wg_gen_key.sh <output_dir> <basename>
set -euo pipefail
outdir="$1"
base="$2"

mkdir -p "$outdir"
priv="$outdir/${base}.key"
pub="$outdir/${base}.pub"

umask 077
wg genkey | tee "$priv" | wg pubkey > "$pub"
echo "PRIVATE=$priv"
echo "PUBLIC=$(cat $pub)"
