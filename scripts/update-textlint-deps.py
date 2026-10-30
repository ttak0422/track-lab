#!/usr/bin/env python3
"""Recompute the textlint npm hash using prefetch-npm-deps from this flake.

Run at the checkout root: nix run .#update-textlint-deps
Check without writing:   nix run .#update-textlint-deps -- --check
Then verify:             nix build .#textlint --no-link
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail on a stale hash without writing")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="checkout root (default: cwd)")
    args = parser.parse_args()
    flake = args.root / "flake.nix"
    lock = args.root / "nix/textlint/package-lock.json"
    source = flake.read_text()
    pattern = re.compile(r'(npmDepsHash\s*=\s*")([^"\n]+)("\s*;)')
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        parser.error("expected exactly one npmDepsHash in flake.nix; refusing an ambiguous update")
    # Use the executable supplied by the Nix app, never an unpinned npx tool.
    result = subprocess.run(["prefetch-npm-deps", str(lock)], text=True, capture_output=True)
    if result.stderr:
        print(result.stderr, file=sys.stderr, end="")
    if result.returncode:
        return result.returncode
    actual = result.stdout.strip()
    if not re.fullmatch(r"sha256-[A-Za-z0-9+/]{43}=", actual):
        parser.error("prefetch-npm-deps did not return one SHA-256 SRI hash")
    current = matches[0].group(2)
    if current == actual:
        print(f"textlint npmDepsHash is current: {actual}")
        return 0
    if args.check:
        print(f"stale textlint npmDepsHash: {current}\nexpected: {actual}\n"
              "Run nix run .#update-textlint-deps, then nix build .#textlint --no-link.",
              file=sys.stderr)
        return 1
    match = matches[0]
    flake.write_text(source[:match.start(2)] + actual + source[match.end(2):])
    print(f"Updated textlint npmDepsHash: {actual}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
