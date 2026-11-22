#!/usr/bin/env bash
set -euo pipefail
source_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' 'Install Python 3.10 or newer from https://www.python.org/downloads/' >&2
  exit 1
fi
if [[ "${1:-}" == "--check-only" ]]; then
  shift
  exec python3 "$source_dir/doctor.py" "$@"
fi
exec python3 "$source_dir/doctor.py" --install "$@"
