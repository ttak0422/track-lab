#!/usr/bin/env python3
"""Extract page-delimited UTF-8 text from a local PDF with Xberg."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time


DEFAULT_TIMEOUT = 30.0


class ExtractionError(Exception):
    def __init__(self, stage: str, code: str, message: str):
        super().__init__(message)
        self.stage = stage
        self.code = code


def run(command: list[str], deadline: float, stage: str) -> subprocess.CompletedProcess[bytes]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ExtractionError(stage, "timeout", "PDF extraction timed out")
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=remaining,
            env={**os.environ, "LC_ALL": "C"},
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ExtractionError(stage, "timeout", "PDF extraction timed out") from error
    except OSError as error:
        raise ExtractionError(stage, "xberg_failed", str(error)) from error
    detail = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode:
        raise ExtractionError(stage, "xberg_failed", detail or f"{command[0]} failed")
    if detail:
        raise ExtractionError(stage, "xberg_diagnostic", detail)
    return result


def normalize(raw: bytes) -> tuple[bytes, int, list[int], str]:
    try:
        result = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as error:
        raise ExtractionError("extract", "invalid_engine_output", "Xberg did not return UTF-8 JSON") from error
    if not isinstance(result, dict):
        raise ExtractionError("validate", "invalid_engine_output", "Xberg output must be an object")
    expected_pages = result.get("page_count")
    if type(expected_pages) is not int or expected_pages <= 0:
        raise ExtractionError("validate", "invalid_page_count", "Xberg did not report a positive page count")
    warnings = result.get("warnings")
    engine = result.get("engine")
    if not isinstance(warnings, list) or not isinstance(engine, str) or not engine.strip():
        raise ExtractionError("validate", "invalid_engine_output", "Xberg omitted warnings or engine identity")
    if warnings:
        raise ExtractionError("extract", "xberg_diagnostic", json.dumps(warnings, ensure_ascii=False))
    pages = result.get("pages")
    if not isinstance(pages, list) or len(pages) != expected_pages:
        raise ExtractionError(
            "validate",
            "page_boundary_mismatch",
            "Xberg page array does not match the PDF page count",
        )
    normalized = []
    empty_pages = []
    for number, item in enumerate(pages, 1):
        if (not isinstance(item, dict) or type(item.get("page_number")) is not int
                or item["page_number"] != number or not isinstance(item.get("content"), str)):
            raise ExtractionError("validate", "page_boundary_mismatch", "Xberg returned missing or unordered physical pages")
        page = item["content"].replace("\r\n", "\n").replace("\r", "\n").strip("\n")
        if "\f" in page:
            raise ExtractionError("validate", "ambiguous_page_boundary", "page text contains a reserved form-feed character")
        if not page.strip():
            page = ""
            empty_pages.append(number)
        normalized.append(page)
    if len(empty_pages) == expected_pages:
        raise ExtractionError(
            "validate",
            "no_extractable_text",
            "all pages contain no extractable text; OCR may be required",
        )
    try:
        text = ("\f".join(normalized) + "\f").encode("utf-8")
    except UnicodeEncodeError as error:
        raise ExtractionError("validate", "invalid_engine_output", "Xberg page text contains invalid Unicode") from error
    return text, expected_pages, empty_pages, engine


def extract(input_path: Path, output_path: Path, original_path: Path, timeout: float) -> dict[str, object]:
    if not math.isfinite(timeout) or timeout <= 0:
        raise ExtractionError("input", "invalid_timeout", "timeout must be greater than zero")
    try:
        resolved = [input_path.resolve(), output_path.resolve(), original_path.resolve()]
        if len(set(resolved)) != len(resolved):
            raise ExtractionError("input", "path_collision", "input PDF, text output, and original output must differ")
    except OSError as error:
        raise ExtractionError("input", "invalid_path", str(error)) from error
    for path in (output_path, original_path):
        if path.exists():
            raise ExtractionError("output", "output_exists", f"refusing to overwrite {path}")
    try:
        source = input_path.read_bytes()
    except OSError as error:
        raise ExtractionError("input", "read_failed", str(error)) from error
    if not source.startswith(b"%PDF-"):
        raise ExtractionError("input", "not_pdf", "input does not have a PDF header")

    engine = shutil.which("track-pdf-engine")
    if not engine:
        raise ExtractionError("dependency", "xberg_missing", "track-pdf-engine must be available; use the Nix extract-pdf app")

    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(prefix="track-clip-pdf-") as directory:
        secured_pdf = Path(directory) / "source.pdf"
        secured_pdf.write_bytes(source)
        raw = run([engine, str(secured_pdf)], deadline, "extract").stdout
        text, pages, empty_pages, engine_identity = normalize(raw)

    created: list[Path] = []
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        original_path.parent.mkdir(parents=True, exist_ok=True)
        with original_path.open("xb") as file:
            created.append(original_path)
            file.write(source)
        with output_path.open("xb") as file:
            created.append(output_path)
            file.write(text)
    except OSError as error:
        for path in created:
            path.unlink(missing_ok=True)
        raise ExtractionError("output", "write_failed", str(error)) from error

    warnings = []
    if empty_pages:
        warnings.append({"code": "empty_pages", "pages": empty_pages})
    return {
        "ok": True,
        "text_path": str(output_path),
        "original_path": str(original_path),
        "page_count": pages,
        "empty_pages": empty_pages,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "text_sha256": hashlib.sha256(text).hexdigest(),
        "extraction_method": f"{engine_identity}; OCR-disabled; LF-normalized; page-edge-LF-trimmed; physical-page-form-feeds",
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="local PDF path")
    parser.add_argument("--text-out", required=True, type=Path, help="new file for extracted UTF-8 text")
    parser.add_argument("--original-out", required=True, type=Path, help="new file for the secured original PDF")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Xberg timeout in seconds (default: 30)")
    arguments = parser.parse_args()
    try:
        result = extract(arguments.input, arguments.text_out, arguments.original_out, arguments.timeout)
    except ExtractionError as error:
        print(json.dumps({"ok": False, "stage": error.stage, "code": error.code, "error": str(error)}), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
