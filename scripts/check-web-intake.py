#!/usr/bin/env python3
"""Offline rehearsal of Web snapshot-v1 consumption and fixed-version citations.

The local HTTP fixture exercises the lab-side manifest consumer without calling the
core fetcher: its SSRF guard correctly refuses loopback addresses. It uses the real,
explicitly supplied track CLI for isolated note/source/cite operations.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import threading
from urllib.request import ProxyHandler, build_opener
from urllib.parse import urlsplit

INSTANT = "instant"
PRECISIONS = {"instant", "date", "local_datetime", "unknown", "absent"}
RFC3339 = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z")
FIXTURE = {
    "html": b"<!doctype html><html><head><title>Fixture article</title></head><body>"
    b"<main><h2>Evidence</h2><p>Revenue was 42 units.</p></main></body></html>",
    "text": "## Evidence\nRevenue was 42 units.\n",
    "published": {"raw": "2026-09-24T09:15:00+09:00", "precision": INSTANT,
                  "timestamp": "2026-09-24T09:15:00+09:00"},
    "modified": {"raw": "2026-09-25", "precision": "date", "timestamp": None},
}


class FixtureHandler(BaseHTTPRequestHandler):
    version = FIXTURE
    requests = 0

    def do_GET(self) -> None:
        type(self).requests += 1
        if self.path.startswith("/article?"):
            self.send_response(302)
            self.send_header("Location", "/canonical")
            self.end_headers()
            return
        if self.path != "/canonical":
            self.send_error(404)
            return
        body = self.version["html"]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_instant(value: object, label: str) -> datetime:
    if not isinstance(value, str) or not RFC3339.fullmatch(value) or value.endswith("-00:00"):
        raise ValueError(f"{label} must be an RFC 3339 string")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must carry a timezone")
    return parsed


def acquire_fixture(opener, source_url: str, container: Path, fixture: dict[str, object]) -> dict[str, object]:
    # This synthetic local HTTP endpoint is isolated to loopback; it makes no external request.
    with opener.open(source_url, timeout=5) as response:
        original = response.read()
        final_url = response.geturl()
    retrieved_at = datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")

    snapshot = Path(tempfile.mkdtemp(prefix="snapshot-", dir=container))
    snapshot.chmod(0o700)
    original_path = snapshot / "original.html"
    text_path = snapshot / "text.md"
    original_path.write_bytes(original)
    text_bytes = str(fixture["text"]).encode("utf-8")
    text_path.write_bytes(text_bytes)
    original_path.chmod(0o600)
    text_path.chmod(0o600)
    return {
        "schema_version": 1,
        "source_url": source_url,
        "final_url": final_url,
        "retrieved_at": retrieved_at,
        "original_path": str(original_path.resolve()),
        "text_path": str(text_path.resolve()),
        "original_sha256": sha256(original),
        "text_sha256": sha256(text_bytes),
        "extraction_method": "readability-v1",
        "published": fixture["published"],
        "modified": fixture["modified"],
    }


def validate_manifest(manifest: object, source_url: str, container: Path) -> tuple[bytes, bytes]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    required = {
        "schema_version", "source_url", "final_url", "retrieved_at", "original_path", "text_path",
        "original_sha256", "text_sha256", "extraction_method", "published", "modified",
    }
    if set(manifest) != required:
        raise ValueError("manifest v1 fields do not match the fixed contract")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("manifest schema_version must be 1")
    if manifest["source_url"] != source_url:
        raise ValueError("manifest schema version or requested source URL does not match")
    for field in ("source_url", "final_url"):
        value = manifest[field]
        parsed = urlsplit(value) if isinstance(value, str) else None
        if parsed is None or parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"manifest {field} must be an HTTP(S) URL")
    parse_instant(manifest["retrieved_at"], "retrieved_at")
    if manifest["extraction_method"] != "readability-v1":
        raise ValueError("manifest extraction_method must be readability-v1")

    resolved_paths: dict[str, Path] = {}
    for key, filename in (("original_path", "original.html"), ("text_path", "text.md")):
        raw_path = manifest[key]
        if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
            raise ValueError(f"{key} must be an absolute path")
        path = Path(raw_path)
        if path.is_symlink() or path.name != filename or not path.parent.name.startswith("snapshot-"):
            raise ValueError(f"{key} is not a fixed file in a snapshot-* child")
        resolved = path.resolve(strict=True)
        # macOS /var is an ancestor alias of /private/var. Accept that canonical
        # container alias, but never a symlinked snapshot child or traversal path.
        if (path != Path(os.path.normpath(path)) or path.parent.is_symlink()
                or resolved.parent.parent != container.resolve(strict=True)):
            raise ValueError(f"{key} escaped the provided snapshot container")
        directory_stat, file_stat = path.parent.stat(), path.stat()
        if (not stat.S_ISDIR(directory_stat.st_mode) or not stat.S_ISREG(file_stat.st_mode)
                or directory_stat.st_mode & 0o777 != 0o700 or file_stat.st_mode & 0o777 != 0o600):
            raise ValueError(f"{key} does not have private snapshot permissions")
        resolved_paths[key] = resolved
    if resolved_paths["original_path"].parent != resolved_paths["text_path"].parent:
        raise ValueError("original.html and text.md must share one snapshot child")

    data = {key: path.read_bytes() for key, path in resolved_paths.items()}
    for path_key, hash_key in (("original_path", "original_sha256"), ("text_path", "text_sha256")):
        expected = manifest[hash_key]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError(f"{hash_key} must be lowercase SHA-256")
        if sha256(data[path_key]) != expected:
            raise ValueError(f"{hash_key} does not match retained file bytes")

    for key in ("published", "modified"):
        metadata = manifest[key]
        if not isinstance(metadata, dict) or set(metadata) != {"raw", "precision", "timestamp"}:
            raise ValueError(f"{key} metadata must contain exactly raw, precision, and timestamp")
        raw = metadata["raw"]
        precision = metadata["precision"]
        if not isinstance(raw, str):
            raise ValueError(f"{key}.raw must be a string")
        if not isinstance(precision, str) or precision not in PRECISIONS:
            raise ValueError(f"unsupported {key}.precision: {precision!r}")
        timestamp = metadata.get("timestamp")
        if precision == INSTANT:
            if not raw or timestamp is None:
                raise ValueError(f"{key} instant metadata requires raw and timestamp")
            parse_instant(timestamp, f"{key}.timestamp")
        elif precision == "absent":
            if raw or timestamp is not None:
                raise ValueError(f"{key} absent metadata must have empty raw and null timestamp")
        elif not raw or timestamp is not None:
            raise ValueError(f"{key}.timestamp must remain null unless precision is instant")

    text = data["text_path"].decode("utf-8")
    if text.startswith("[Source]"):
        raise ValueError("snapshot text.md must not contain a Source header")
    return data["original_path"], data["text_path"]


def manifest_container(manifest: dict[str, object]) -> Path:
    raw_path = manifest.get("original_path")
    if not isinstance(raw_path, str) or not Path(raw_path).is_absolute():
        raise ValueError("manifest original_path must be absolute")
    original_path = Path(raw_path)
    snapshot = original_path.parent
    if original_path.name != "original.html" or not snapshot.name.startswith("snapshot-"):
        raise ValueError("manifest original_path must name original.html in a snapshot-* child")
    return snapshot.parent.resolve(strict=True)


def make_snapshot(container: Path, template: dict[str, object], original: bytes,
                  text: bytes, *, retrieved_at: str | None = None) -> dict[str, object]:
    snapshot = Path(tempfile.mkdtemp(prefix="snapshot-", dir=container))
    original_path = snapshot / "original.html"
    text_path = snapshot / "text.md"
    original_path.write_bytes(original)
    text_path.write_bytes(text)
    original_path.chmod(0o600)
    text_path.chmod(0o600)
    return {
        **template,
        "retrieved_at": retrieved_at or datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        "original_path": str(original_path.resolve()),
        "text_path": str(text_path.resolve()),
        "original_sha256": sha256(original),
        "text_sha256": sha256(text),
        "extraction_method": "readability-v1",
    }


def self_test() -> int:
    with tempfile.TemporaryDirectory(prefix="track-web-manifest-test-") as temporary:
        container = Path(temporary)
        source_url = "https://fixture.example/article"
        original = b"<html>fixture</html>"
        text = b"## Evidence\nFixture quote.\n"
        manifest = make_snapshot(container, {
            "schema_version": 1, "source_url": source_url, "final_url": source_url,
            "published": {"raw": "2026-09-24", "precision": "date", "timestamp": None},
            "modified": {"raw": "", "precision": "absent", "timestamp": None},
        }, original, text, retrieved_at="2026-09-27T00:00:00Z")
        assert validate_manifest(manifest, source_url, container) == (original, text)

        # An ancestor alias (e.g. /var -> /private/var) is not an escape.
        alias = container / "container-alias"
        alias.symlink_to(container.resolve(), target_is_directory=True)
        aliased = dict(manifest)
        for key in ("original_path", "text_path"):
            relative = Path(manifest[key]).relative_to(container.resolve())
            aliased[key] = str(alias / relative)
        assert validate_manifest(aliased, source_url, alias) == (original, text)

        def rejects(candidate: dict[str, object], message: str) -> None:
            try:
                validate_manifest(candidate, source_url, container)
            except ValueError:
                return
            raise AssertionError(message)

        damaged_hash = {**manifest, "original_sha256": "0" * 64}
        rejects(damaged_hash, "tampered hash was accepted")
        rejects({**manifest, "schema_version": True}, "boolean schema version was accepted")
        rejects({**manifest, "uncontracted": True}, "unexpected manifest field was accepted")
        rejects({key: value for key, value in manifest.items() if key != "modified"},
                "missing manifest field was accepted")
        rejects({**manifest, "retrieved_at": "2026-09-27"}, "date-only retrieval time was accepted")
        rejects({**manifest, "retrieved_at": "2026-09-27T00:00:00-00:00"},
                "unknown retrieval offset was accepted")
        date_timestamp = {
            **manifest,
            "published": {"raw": "2026-09-24", "precision": "date", "timestamp": "2026-09-24T00:00:00Z"},
        }
        rejects(date_timestamp, "date precision was promoted to an instant")
        unknown_timestamp = {
            **manifest,
            "published": {"raw": "unclear", "precision": "unknown", "timestamp": "2026-09-24T00:00:00Z"},
        }
        rejects(unknown_timestamp, "unknown publication time was promoted to an instant")
        unsafe_path = {**manifest, "original_path": str(Path(manifest["original_path"]).parent / ".." / "original.html")}
        rejects(unsafe_path, "non-normalized path was accepted")
        text_path = Path(manifest["text_path"])
        text_path.chmod(0o644)
        rejects(manifest, "publicly readable text snapshot was accepted")
        text_path.chmod(0o600)
        text_path.unlink()
        os.mkfifo(text_path, 0o600)
        rejects(manifest, "non-regular text snapshot was accepted")
    print("Web manifest self-test passed: v1 shape, retained hashes, paths, permissions, and precision.")
    return 0


def verify_manifest_file(path: Path) -> int:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not isinstance(manifest.get("source_url"), str):
        raise ValueError("manifest file must contain a v1 source_url")
    original, text = validate_manifest(manifest, manifest["source_url"], manifest_container(manifest))
    print(json.dumps({
        "manifest": "verified", "retrieved_at": manifest["retrieved_at"],
        "original_sha256": sha256(original), "text_sha256": sha256(text),
    }))
    return 0


def run_integration(binary_path: Path, input_manifest: Path | None) -> int:
    if not binary_path.is_file() or not os.access(binary_path, os.X_OK):
        raise SystemExit(f"track binary is not executable: {binary_path}")

    server = thread = opener = None
    fixture_state = {"current": FIXTURE}
    if input_manifest is None:
        FixtureHandler.requests = 0
        FixtureHandler.version = fixture_state["current"]
        server = ThreadingHTTPServer(("127.0.0.1", 0), FixtureHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        opener = build_opener(ProxyHandler({}))

    try:
        with tempfile.TemporaryDirectory(prefix="track-web-intake-") as temporary:
            root = Path(temporary)
            vault = root / "vault"
            snapshots = root / "snapshots"
            snapshots.mkdir()
            env = {key: value for key, value in os.environ.items() if not key.startswith("TRACK_")}
            env.update(
                TRACK_CONFIG=str(root / "config.yml"),
                TRACK_VAULT=str(vault),
                TRACK_CACHE_DIR=str(root / "cache"),
            )

            def invoke(args: list[object], *, body: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
                return subprocess.run(
                    [str(binary_path), *map(str, args)], env=env, input=body,
                    capture_output=True, check=False,
                )

            def track(*args: object, body: bytes | None = None) -> object:
                result = invoke(list(args), body=body)
                assert result.returncode == 0, (result.stdout + result.stderr).decode("utf-8", "replace")
                if args[0] == "export":
                    return result.stdout.decode("utf-8")
                return json.loads(result.stdout)

            def track_fails(*args: object) -> str:
                result = invoke(list(args))
                assert result.returncode != 0, result.stdout.decode("utf-8", "replace")
                return (result.stderr + result.stdout).decode("utf-8", "replace")

            track("init")
            fixture_url = f"http://127.0.0.1:{server.server_port}/article?edition=1" if server else ""
            if input_manifest is None:
                assert opener is not None
                first = acquire_fixture(opener, fixture_url, snapshots, fixture_state["current"])
                first_container = snapshots
                assert first["final_url"].endswith("/canonical")
                assert first["source_url"] != first["final_url"]
                assert first["modified"]["timestamp"] is None
            else:
                first = json.loads(input_manifest.read_text(encoding="utf-8"))
                first_container = manifest_container(first)
            source_url = first["source_url"]
            original_bytes, text_bytes = validate_manifest(first, source_url, first_container)
            first_text = text_bytes.decode("utf-8")
            first_lines = first_text.splitlines()
            first_line_number = next((i for i, line in enumerate(first_lines, 1) if line.strip()), None)
            if first_line_number is None:
                raise ValueError("manifest text.md is empty; no citeable line exists")
            first_quote = first_lines[first_line_number - 1]

            damaged = {**first, "text_sha256": "0" * 64}
            try:
                validate_manifest(damaged, source_url, first_container)
                raise AssertionError("tampered manifest hash was accepted")
            except ValueError as error:
                assert "does not match" in str(error)
            assert track("notes")["notes"] == []

            title = "Fixture article"
            track("new", "--title", title, "--tag", "clip", body=text_bytes)
            note_id = int(track("resolve", "--term", title)["note_id"])

            def save(manifest: dict[str, object]) -> dict[str, object]:
                return track(
                    "source", "save", "--id", note_id, "--source", manifest["source_url"],
                    "--format", "text/html", "--at", manifest["retrieved_at"],
                    "--original", manifest["original_path"],
                )

            saved = save(first)
            assert saved["created"] is True
            first_record = saved["record"]
            first_export = track("export", "--id", note_id)
            assert first_record["note_id"] == note_id
            assert first_record["original_hash"] == sha256(original_bytes)
            assert first_record["content_hash"] == sha256(first_export.encode("utf-8"))
            assert parse_instant(first_record["recorded_at"], "recorded_at") == parse_instant(first["retrieved_at"], "retrieved_at").astimezone(timezone.utc)

            def cite(record: dict[str, object], text: str, expected: str) -> dict[str, object]:
                lines = text.splitlines()
                line_number = next((i for i, line in enumerate(lines, 1) if expected in line), None)
                if line_number is None:
                    raise AssertionError(f"citation quote is not in fixed source text: {expected!r}")
                result = track("cite", "--id", record["note_id"], "--version", record["version"],
                               "--start-line", line_number, "--end-line", line_number)
                assert result["pinned"] is True
                assert result["note_id"] == record["note_id"] and result["version"] == record["version"]
                assert result["content_hash"] == record["content_hash"]
                assert expected in result["body"]
                return result

            cite(first_record, first_text, first_quote)
            if input_manifest is None:
                assert opener is not None
                repeated = acquire_fixture(opener, fixture_url, snapshots, fixture_state["current"])
            else:
                repeated = first
            validate_manifest(repeated, source_url, snapshots if input_manifest is None else first_container)
            reused = save(repeated)
            assert reused["created"] is False and reused["record"] == first_record
            assert len(track("source", "list", "--id", note_id)["versions"]) == 1

            def reference(manifest: dict[str, object], record: dict[str, object]) -> str:
                dates = {key: manifest[key] for key in ("published", "modified")}
                return (
                    f"[^1]: [Fixture article]({manifest['source_url']}) — final URL: {manifest['final_url']}; "
                    f"[[Fixture article]], version `{record['version']}`, position `line {first_line_number}`; "
                    f"content_sha256 `{record['content_hash']}`, original_sha256 `{record['original_hash']}`; "
                    f"text_sha256 `{manifest['text_sha256']}`, extraction_method `{manifest['extraction_method']}`; "
                    f"retrieved_at `{manifest['retrieved_at']}`; date metadata `{json.dumps(dates, sort_keys=True)}`.\n"
                )

            citation_ref = reference(first, first_record)
            report_body = f"from [[Fixture research]]\n\n{first_quote}[^1]\n\n" + citation_ref
            watch_body = (
                f"from [[Fixture topic 定点観測]]\n\n## 当日の動き\n{first_quote}[^1]\n\n"
                "## 引き継ぎ\n固定版の引用を確認済み。\n\n" + citation_ref
            )
            track("new", "--title", "Fixture research report", "--tag", "report", body=report_body.encode())
            track("new", "--title", "20260927 fixture daily", "--tag", "daily", body=watch_body.encode())

            if input_manifest is None:
                corrected_fixture = {
                    **FIXTURE,
                    "html": b"<!doctype html><html><body><main><h2>Evidence</h2>"
                    b"<p>Revenue was 47 units.</p></main></body></html>",
                    "text": "## Evidence\nRevenue was 47 units.\n",
                    "modified": {"raw": "2026-09-26T11:00:00+09:00", "precision": INSTANT,
                                 "timestamp": "2026-09-26T11:00:00+09:00"},
                }
                fixture_state["current"] = corrected_fixture
                FixtureHandler.version = corrected_fixture
                assert opener is not None
                corrected = acquire_fixture(opener, fixture_url, snapshots, corrected_fixture)
                corrected_container = snapshots
            else:
                corrected_text = (first_text.rstrip() + "\n\n## Fixture correction\nLab-only correction sentinel.\n").encode()
                corrected_original = original_bytes + b"\n<!-- lab-only correction fixture -->"
                corrected = make_snapshot(snapshots, first, corrected_original, corrected_text)
                corrected_container = snapshots
            corrected_original, corrected_text_bytes = validate_manifest(corrected, source_url, corrected_container)
            track("update", "--id", note_id, "--body", corrected_text_bytes.decode("utf-8"))
            corrected_saved = save(corrected)
            assert corrected_saved["created"] is True
            second_record = corrected_saved["record"]
            assert second_record["version"] != first_record["version"]
            assert second_record["original_hash"] == sha256(corrected_original)
            assert len(track("source", "list", "--id", note_id)["versions"]) == 2
            correction_quote = ("Revenue was 47 units." if input_manifest is None else "Lab-only correction sentinel.")
            old_citation = cite(first_record, first_text, first_quote)
            new_citation = cite(second_record, corrected_text_bytes.decode("utf-8"), correction_quote)
            assert correction_quote not in old_citation["body"]
            assert first_quote not in new_citation["body"]
            assert first["retrieved_at"] in track("export", "--title", "Fixture research report")
            assert first["retrieved_at"] in track("export", "--title", "20260927 fixture daily")
            if input_manifest is None:
                assert FixtureHandler.requests == 6
            track_fails("cite", "--id", note_id, "--version", "not-a-version", "--heading", "Evidence")

            print(json.dumps({
                "web_intake": "passed", "vault_isolated": vault.is_relative_to(root),
                "fixture_http_requests": FixtureHandler.requests if input_manifest is None else 0,
                "manifest_v1": "passed",
                "fixed_cite_reuse_correction": "passed", "report_watch_provenance": "passed",
            }))
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="validate v1 fixtures without network or track")
    parser.add_argument("--verify-only", action="store_true", help="verify an existing manifest and its files")
    parser.add_argument("--manifest", type=Path, help="existing snapshot manifest to consume")
    parser.add_argument("--track", type=Path, help="explicit compatible track binary for isolated CLI rehearsal")
    args = parser.parse_args()
    if args.self_test:
        if args.verify_only or args.manifest or args.track:
            parser.error("--self-test cannot be combined with other modes")
        return self_test()
    if args.verify_only:
        if not args.manifest or args.track:
            parser.error("--verify-only requires --manifest and does not accept --track")
        return verify_manifest_file(args.manifest)
    if not args.track:
        parser.error("--track /absolute/path/to/compatible/track is required")
    if args.manifest and not args.manifest.is_file():
        parser.error(f"manifest file not found: {args.manifest}")
    return run_integration(args.track.resolve(strict=True), args.manifest.resolve(strict=True) if args.manifest else None)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"check-web-intake: {error}", file=sys.stderr)
        raise SystemExit(1)
