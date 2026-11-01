#!/usr/bin/env python3
"""Exercise the CLI's no-write guarantees without fetching dependencies."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name("update-textlint-deps.py")
OLD = "sha256-" + "A" * 43 + "="
NEW = "sha256-" + "B" * 43 + "="


class UpdateHashTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "nix/textlint").mkdir(parents=True)
        (self.root / "nix/textlint/package-lock.json").write_text("{}\n")
        self.flake = self.root / "flake.nix"
        self.original = f'{{ npmDepsHash = "{OLD}"; }}\n'
        self.flake.write_text(self.original)
        self.tool = self.root / "prefetch-npm-deps"
        self.tool.write_text(f"#!/bin/sh\nprintf '%s\\n' '{NEW}'\n")
        self.tool.chmod(0o755)

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), "--root", str(self.root), *args],
                              env={**os.environ, "PATH": str(self.root) + os.pathsep + os.environ["PATH"]},
                              text=True, capture_output=True)

    def test_check_does_not_write_and_update_is_idempotent(self):
        result = self.run_cli("--check")
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(self.flake.read_text(), self.original)
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.flake.read_text(), self.original.replace(OLD, NEW))
        self.assertEqual(self.run_cli("--check").returncode, 0)

    def test_prefetch_failure_and_invalid_output_do_not_write(self):
        for command in ["exit 7", "printf 'invalid-output\\n'"]:
            self.tool.write_text("#!/bin/sh\n" + command + "\n")
            self.assertNotEqual(self.run_cli().returncode, 0)
            self.assertEqual(self.flake.read_text(), self.original)

    def test_ambiguous_hash_does_not_write(self):
        duplicated = self.original + self.original
        self.flake.write_text(duplicated)
        self.assertNotEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.flake.read_text(), duplicated)


if __name__ == "__main__":
    unittest.main()
