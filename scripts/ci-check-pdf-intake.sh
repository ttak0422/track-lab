#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  printf '%s\n' "usage: $0 /absolute/path/to/compatible/track" >&2
  exit 2
fi

repo_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
track_binary="$1"
if [[ "$track_binary" != /* ]]; then
  track_binary="$PWD/$track_binary"
fi

exec nix run "path:${repo_root}#check-pdf-intake" -- "$track_binary"
