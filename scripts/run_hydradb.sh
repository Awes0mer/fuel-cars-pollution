#!/usr/bin/env bash
# Start a self-hosted HydraDB v0.4.0 graph-node in local mode.
#
# - a NEW, EMPTY storage directory per run (never an existing data directory)
# - a NEW random auth token per run
# - usage reporting OFF
# - listens on 127.0.0.1 only (Bolt 7687, HTTP 8443, admin 9090)
# Settings follow the "Run a local server" section of HydraDB's README.
#
# Usage (inside WSL):  bash scripts/run_hydradb.sh <graph-node binary> <token output file>
set -euo pipefail

BIN="${1:?path to graph-node binary}"
TOKEN_OUT="${2:?file to write the token to}"

RUN_DIR="$HOME/fcp-hydradb-runs/$(date -u +%Y%m%dT%H%M%SZ)-$$"
if [ -e "$RUN_DIR" ]; then echo "run dir already exists: $RUN_DIR" >&2; exit 1; fi
mkdir -p "$RUN_DIR/store" "$RUN_DIR/cache"
if [ -n "$(ls -A "$RUN_DIR/store")" ]; then echo "store not empty" >&2; exit 1; fi

TOKEN="$(head -c 32 /dev/urandom | od -An -tx1 | tr -d ' \n')"
printf '%s\n' "$TOKEN" > "$RUN_DIR/auth-token"
chmod 600 "$RUN_DIR/auth-token"
mkdir -p "$(dirname "$TOKEN_OUT")"
printf '%s\n' "$TOKEN" > "$TOKEN_OUT"

export CLOUD_PROVIDER=local
export LOCAL_PATH="$RUN_DIR/store"
export GRAPH_NAMESPACE=default
export GRAPH_ID=default
export GRAPH_CELL_ID=cell-0
export GRAPH_CELLS=cell-0
export GRAPH_NODE_ID=node-0
export GRAPH_BOLT_NODE_ADDRESSES=node-0=127.0.0.1:7687
export GRAPH_ADVERTISED_BOLT_ADDR=127.0.0.1:7687
export GRAPH_DATA_CACHE_DIR="$RUN_DIR/cache"
export GRAPH_AUTH_TOKEN_FILE="$RUN_DIR/auth-token"
export GRAPH_ALLOW_PLAINTEXT=true
# graph-node defaults to 0.0.0.0; bind every listener to loopback only.
export GRAPH_BOLT_ADDR=127.0.0.1:7687
export GRAPH_HTTP_ADDR=127.0.0.1:8443
export GRAPH_ADMIN_ADDR=127.0.0.1:9090
export GRAPH_USAGE_REPORT_ENABLED=false
export RUST_MIN_STACK=33554432

echo "hydradb run dir: $RUN_DIR (new, empty)"
echo "usage reporting: GRAPH_USAGE_REPORT_ENABLED=$GRAPH_USAGE_REPORT_ENABLED"
exec "$BIN"
