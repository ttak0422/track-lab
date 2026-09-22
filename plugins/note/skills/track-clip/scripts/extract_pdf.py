#!/usr/bin/env python3
"""Extract page-delimited UTF-8 text from a local PDF with Poppler."""

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
    detail = result.stderr.decode("utf-8", "replace").strip()
    if result.returncode:
        raise ExtractionError(stage, "poppler_failed", detail or f"{command[0]} failed")
    if detail:
        raise ExtractionError(stage, "poppler_diagnostic", detail)
    return result


def page_count(pdfinfo_output: bytes) -> int:
    for line in pdfinfo_output.decode("utf-8", "replace").splitlines():
        name, separator, value = line.partition(":")
        if separator and name.strip() == "Pages":
            try:
                pages = int(value.strip())
            except ValueError as error:
                raise ExtractionError("inspect", "invalid_page_count", "pdfinfo returned an invalid page count") from error
            if pages > 0:
                return pages
    raise ExtractionError("inspect", "missing_page_count", "pdfinfo did not report a positive page count")


def normalize(raw: bytes, expected_pages: int) -> tuple[bytes, list[int]]:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ExtractionError("extract", "invalid_utf8", "pdftotext did not return UTF-8") from error
    decoded = decoded.replace("\r\n", "\n").replace("\r", "\n")
    if not decoded.endswith("\f"):
        raise ExtractionError("validate", "missing_page_terminator", "pdftotext output lacks its final page terminator")
    pages = decoded.split("\f")
    if pages and pages[-1] == "":
        pages.pop()
    if len(pages) != expected_pages:
        raise ExtractionError(
            "validate",
            "page_boundary_mismatch",
            f"extracted {len(pages)} page boundaries for a {expected_pages}-page PDF",
        )
    normalized = []
    empty_pages = []
    for number, page in enumerate(pages, 1):
        page = page.strip("\n")
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
    return ("\f".join(normalized) + "\f").encode("utf-8"), empty_pages


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

    pdfinfo = shutil.which("pdfinfo")
    pdftotext = shutil.which("pdftotext")
    if not pdfinfo or not pdftotext:
        raise ExtractionError("dependency", "poppler_missing", "pdfinfo and pdftotext must be available on PATH")

    deadline = time.monotonic() + timeout
    with tempfile.TemporaryDirectory(prefix="track-clip-pdf-") as directory:
        secured_pdf = Path(directory) / "source.pdf"
        secured_pdf.write_bytes(source)
        pages = page_count(run([pdfinfo, str(secured_pdf)], deadline, "inspect").stdout)
        raw_text = run(
            [pdftotext, "-enc", "UTF-8", "-eol", "unix", str(secured_pdf), "-"],
            deadline,
            "extract",
        ).stdout
        text, empty_pages = normalize(raw_text, pages)

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
        "extraction_method": "poppler-pdftotext -enc UTF-8 -eol unix; LF-normalized; page-edge-LF-trimmed",
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="local PDF path")
    parser.add_argument("--text-out", required=True, type=Path, help="new file for extracted UTF-8 text")
    parser.add_argument("--original-out", required=True, type=Path, help="new file for the secured original PDF")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="total Poppler timeout in seconds (default: 30)")
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
