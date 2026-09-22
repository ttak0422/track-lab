#!/usr/bin/env python3
"""Fixed regression checks for extract_pdf.py."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import time


SCRIPT = Path(__file__).parents[1] / "scripts" / "extract_pdf.py"


def pdf(page_texts: list[str]) -> bytes:
    objects: list[bytes] = []
    page_ids = []
    for _ in page_texts:
        page_ids.append(len(objects) + 3)
        objects.extend([b"", b""])
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        f"<< /Type /Pages /Kids [{' '.join(f'{item} 0 R' for item in page_ids)}] /Count {len(page_ids)} >>".encode(),
    ]
    font_id = 3 + 2 * len(page_texts)
    for index, text in enumerate(page_texts):
        content_id = 4 + 2 * index
        escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        content = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode() if text else b""
        objects.append(f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> /MediaBox [0 0 612 792] /Contents {content_id} 0 R >>".encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        result.extend(f"{offset:010d} 00000 n \n".encode())
    result.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(result)


def invoke(source: Path, output: Path, *, timeout: float = 30, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    original = output.with_suffix(".original.pdf")
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--text-out", str(output), "--original-out", str(original), "--timeout", str(timeout)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        check=False,
    )


def success_cases(directory: Path) -> None:
    for name, pages, expected, empty in [
        ("one", ["one"], b"one\f", []),
        ("middle-empty", ["one", "", "three"], b"one\f\fthree\f", [2]),
        ("trailing-empty", ["one", ""], b"one\f\f", [2]),
        ("printed-numbers", ["ix", "1"], b"ix\f1\f", []),
    ]:
        source = directory / f"{name}.pdf"
        output = directory / f"{name}.txt"
        source_bytes = pdf(pages)
        source.write_bytes(source_bytes)
        result = invoke(source, output)
        assert result.returncode == 0, result.stderr
        metadata = json.loads(result.stdout)
        assert output.read_bytes() == expected
        assert metadata["page_count"] == len(pages)
        assert metadata["empty_pages"] == empty
        assert metadata["source_sha256"] == hashlib.sha256(source_bytes).hexdigest()
        assert Path(metadata["original_path"]).read_bytes() == source_bytes
        assert metadata["text_sha256"] == hashlib.sha256(expected).hexdigest()
        assert bool(metadata["warnings"]) == bool(empty)


def failure_cases(directory: Path) -> None:
    image_only = directory / "image-only.pdf"
    image_only.write_bytes(pdf(["", ""]))
    output = directory / "image-only.txt"
    result = invoke(image_only, output)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "no_extractable_text"
    assert not output.exists()
    assert not output.with_suffix(".original.pdf").exists()

    damaged = directory / "damaged.pdf"
    damaged.write_bytes(b"%PDF-not-a-pdf")
    result = invoke(damaged, directory / "damaged.txt")
    assert result.returncode == 1 and json.loads(result.stderr)["stage"] == "inspect"

    existing = directory / "existing.txt"
    existing.write_text("keep", encoding="utf-8")
    result = invoke(image_only, existing)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "output_exists"
    assert existing.read_text(encoding="utf-8") == "keep"


def consistency_and_timeout(directory: Path) -> None:
    tools = directory / "fake-poppler"
    tools.mkdir()
    fake = """#!/usr/bin/env python3
import pathlib, sys, time
if pathlib.Path(sys.argv[0]).name == 'pdfinfo':
    print('Pages:', __import__('os').environ.get('FAKE_PAGE_COUNT', '1'))
else:
    time.sleep(float(__import__('os').environ.get('FAKE_DELAY', '0')))
    data = pathlib.Path(sys.argv[-2]).read_bytes()
    print('first' if b'FIRST' in data else 'second', end=__import__('os').environ.get('FAKE_END', '\\f'))
    print(__import__('os').environ.get('FAKE_WARNING', ''), end='', file=sys.stderr)
"""
    for name in ("pdfinfo", "pdftotext"):
        path = tools / name
        path.write_text(textwrap.dedent(fake), encoding="utf-8")
        path.chmod(0o755)
    environment = {**os.environ, "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}", "FAKE_DELAY": "0.3"}
    source = directory / "raced.pdf"
    first = b"%PDF-FIRST"
    source.write_bytes(first)
    output = directory / "raced.txt"
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), str(source), "--text-out", str(output), "--original-out", str(output.with_suffix('.original.pdf'))],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
    )
    time.sleep(0.1)
    source.write_bytes(b"%PDF-SECOND")
    stdout, stderr = process.communicate()
    assert process.returncode == 0, stderr
    metadata = json.loads(stdout)
    assert output.read_bytes() == b"first\f"
    assert metadata["source_sha256"] == hashlib.sha256(first).hexdigest()
    assert output.with_suffix(".original.pdf").read_bytes() == first

    timeout_output = directory / "timeout.txt"
    result = invoke(source, timeout_output, timeout=0.05, env=environment)
    error = json.loads(result.stderr)
    assert result.returncode == 1 and error["code"] == "timeout"
    assert not timeout_output.exists()
    assert not timeout_output.with_suffix(".original.pdf").exists()

    for name, variable, value, code in [
        ("diagnostic", "FAKE_WARNING", "Syntax Warning", "poppler_diagnostic"),
        ("unterminated", "FAKE_END", "", "missing_page_terminator"),
        ("mismatch", "FAKE_PAGE_COUNT", "2", "page_boundary_mismatch"),
    ]:
        case_output = directory / f"{name}.txt"
        case_environment = {**environment, "FAKE_DELAY": "0", variable: value}
        result = invoke(source, case_output, env=case_environment)
        assert result.returncode == 1 and json.loads(result.stderr)["code"] == code
        assert not case_output.exists()
        assert not case_output.with_suffix(".original.pdf").exists()

    result = invoke(source, directory / "nan.txt", timeout=float("nan"), env=environment)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "invalid_timeout"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="track-clip-pdf-test-") as temporary:
        directory = Path(temporary)
        success_cases(directory)
        failure_cases(directory)
        consistency_and_timeout(directory)
    print("extract_pdf: all checks passed")


if __name__ == "__main__":
    main()
