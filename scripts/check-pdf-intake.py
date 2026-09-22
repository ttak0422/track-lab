#!/usr/bin/env python3
"""Offline PDF intake rehearsal in an isolated temporary vault."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


assert len(sys.argv) in (2, 3), "usage: check-pdf-intake.py /absolute/path/to/track [extractor-root]"
binary = str(Path(sys.argv[1]).resolve(strict=True))
root = Path(sys.argv[2]).resolve(strict=True) if len(sys.argv) == 3 else Path(__file__).parents[1]
extractor = root / "plugins/note/skills/track-clip/scripts/extract_pdf.py"
fixture = root / "plugins/note/skills/track-clip/tests/test_extract_pdf.py"
assert extractor.is_file() and fixture.is_file()

spec = importlib.util.spec_from_file_location("pdf_fixture", fixture)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


with tempfile.TemporaryDirectory(prefix="track-pdf-intake-") as temporary:
    directory = Path(temporary)
    env = {key: value for key, value in os.environ.items() if not key.startswith("TRACK_")}
    env.update(
        TRACK_CONFIG=str(directory / "config.yml"),
        TRACK_VAULT=str(directory / "vault"),
        TRACK_CACHE_DIR=str(directory / "cache"),
    )

    def invoke(command: list[str], *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, env=environment or env, text=True, capture_output=True)

    def track(*args: object) -> object:
        result = invoke([binary, *map(str, args)])
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout if args[0] == "export" else json.loads(result.stdout)

    def track_fails(*args: object) -> dict[str, object]:
        result = invoke([binary, *map(str, args)])
        assert result.returncode != 0, result.stdout
        return json.loads(result.stderr or result.stdout)

    def extract(name: str, pages: list[str]) -> tuple[dict[str, object], str, bytes, Path]:
        source = directory / f"{name}.pdf"
        text_path = directory / "acquired" / f"{name}.txt"
        original_path = directory / "acquired" / f"{name}.pdf"
        source_bytes = module.pdf(pages)
        source.write_bytes(source_bytes)
        result = invoke(
            [sys.executable, str(extractor), str(source), "--text-out", str(text_path),
             "--original-out", str(original_path)],
            environment=os.environ.copy(),
        )
        assert result.returncode == 0, result.stderr
        metadata = json.loads(result.stdout)
        body = text_path.read_text(encoding="utf-8")
        assert metadata["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
        assert metadata["text_sha256"] == hashlib.sha256(body.encode()).hexdigest()
        return metadata, body, source_bytes, source

    def new(title: str, body: str) -> int:
        track("new", "--title", title, "--body", body)
        return int(track("resolve", "--term", title)["note_id"])

    def save(note_id: int, source: str, original: str, at: str) -> dict[str, object]:
        return track("source", "save", "--id", note_id, "--source", source,
                     "--format", "application/pdf", "--at", at, "--original", original)

    track("init")

    failed_source = directory / "broken.pdf"
    failed_text = directory / "failed" / "broken.txt"
    failed_original = directory / "failed" / "broken.pdf"
    failed_source.write_bytes(b"%PDF-not-a-real-pdf")
    failure = invoke([sys.executable, str(extractor), str(failed_source), "--text-out", str(failed_text),
                      "--original-out", str(failed_original)], environment=os.environ.copy())
    assert failure.returncode != 0 and not failed_text.exists() and not failed_original.exists()
    assert json.loads(failure.stderr)["ok"] is False
    assert track("notes")["notes"] == []

    one, one_body, _, _ = extract("one-page", ["Only page"])
    assert one["page_count"] == 1 and one["empty_pages"] == [] and one_body == "Only page\f"
    one_id = new("One-page PDF", one_body)
    one_save = save(one_id, "file:///fixtures/one-page.pdf", one["original_path"], "2026-09-18T09:00:00+09:00")
    one_record = one_save["record"]
    assert track("cite", "--id", one_record["note_id"], "--version", one_record["version"], "--page", 1)["body"] == "Only page"
    track_fails("cite", "--id", one_record["note_id"], "--version", one_record["version"], "--page", 2)

    first, first_body, first_bytes, mutable_source = extract(
        "financial", ["Revenue\n1200", "", "Unit\nJPY million\nPeriod\nFY2025", ""]
    )
    assert first["page_count"] == 4 and first["empty_pages"] == [2, 4]
    mutable_source.write_bytes(module.pdf(["MUTATED INPUT PATH"]))
    note_id = new("Financial PDF", first_body)
    before_count = len(track("notes")["notes"])
    first_save = save(note_id, "https://example.invalid/financial.pdf", first["original_path"],
                      "2026-09-18T09:30:00+09:00")
    assert first_save["created"] is True
    first_record = first_save["record"]
    assert first_record["note_id"] == note_id
    assert first_record["recorded_at"] == "2026-09-18T00:30:00Z"
    assert first_record["original_hash"] == hashlib.sha256(first_bytes).hexdigest()
    assert first_record["original_hash"] != hashlib.sha256(mutable_source.read_bytes()).hexdigest()
    saved_body = track("export", "--id", note_id)
    assert first_record["content_hash"] == hashlib.sha256(saved_body.encode()).hexdigest()
    assert first["text_sha256"] != first_record["content_hash"]

    repeated = save(note_id, "https://example.invalid/financial.pdf", first["original_path"],
                    "2026-09-20T11:00:00+09:00")
    assert repeated["created"] is False and repeated["record"] == first_record
    assert repeated["record"]["recorded_at"] == first_record["recorded_at"]
    assert len(track("source", "list", "--id", note_id)["versions"]) == 1
    assert len(track("notes")["notes"]) == before_count

    for page, quote in [(1, "1200"), (3, "JPY million"), (3, "FY2025")]:
        citation = track("cite", "--id", first_record["note_id"], "--version", first_record["version"],
                         "--page", page)
        assert citation["pinned"] is True and citation["content_hash"] == first_record["content_hash"]
        assert citation["note_id"] == first_record["note_id"] and citation["version"] == first_record["version"]
        assert citation["page"] == page and quote in citation["body"]
    assert track("cite", "--id", note_id, "--version", first_record["version"], "--page", 2)["body"] == ""
    assert track("cite", "--id", note_id, "--version", first_record["version"], "--page", 4)["body"] == ""
    track_fails("cite", "--id", note_id, "--version", first_record["version"], "--page", 5)

    corrected, corrected_body, _, _ = extract(
        "financial-corrected", ["Revenue\n1250", "", "Unit\nJPY million\nPeriod\nFY2025", ""]
    )
    track("update", "--id", note_id, "--body", corrected_body)
    corrected_save = save(note_id, "https://example.invalid/financial.pdf", corrected["original_path"],
                          "2026-09-19T10:00:00+09:00")
    assert corrected_save["created"] is True
    corrected_record = corrected_save["record"]
    assert corrected_record["recorded_at"] == "2026-09-19T01:00:00Z"
    assert corrected_record["version"] != first_record["version"]
    assert len(track("source", "list", "--id", note_id)["versions"]) == 2
    old_quote = track("cite", "--id", note_id, "--version", first_record["version"], "--page", 1)
    new_quote = track("cite", "--id", note_id, "--version", corrected_record["version"], "--page", 1)
    assert "1200" in old_quote["body"] and "1250" not in old_quote["body"]
    assert "1250" in new_quote["body"] and "1200" not in new_quote["body"]

    print(json.dumps({"pdf_intake": "passed", "versions": 2, "physical_pages": 4}))
