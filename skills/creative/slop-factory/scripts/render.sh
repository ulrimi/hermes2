#!/usr/bin/env bash
# Thin wrapper around the slop-factory sibling repo's render.py.
# Usage: render.sh <script.yaml> [extra render.py args]
set -euo pipefail

REPO="${SLOP_FACTORY_REPO:-$HOME/code/slop-factory}"

if [[ ! -d "$REPO" ]]; then
  echo "slop-factory repo not found at $REPO" >&2
  echo "Set SLOP_FACTORY_REPO env var or clone/scaffold the repo." >&2
  exit 1
fi

if [[ $# -lt 1 ]]; then
  echo "Usage: render.sh <script.yaml> [extra render.py args]" >&2
  exit 2
fi

SCRIPT="$1"
shift

# Resolve script path: if relative and not found, try ${REPO}/scripts/${SCRIPT}
if [[ ! -f "$SCRIPT" && -f "$REPO/scripts/$SCRIPT" ]]; then
  SCRIPT="$REPO/scripts/$SCRIPT"
fi

cd "$REPO"

if [[ -f venv/bin/activate ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

exec python render.py "$SCRIPT" "$@"
