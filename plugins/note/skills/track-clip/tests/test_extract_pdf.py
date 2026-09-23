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


SCRIPT = Path(sys.argv[1]) if __name__ == "__main__" and len(sys.argv) == 2 else Path(__file__).parents[1] / "scripts" / "extract_pdf.py"


def pdf(page_texts: list[str]) -> bytes:
    unicode_font = any(ord(char) > 127 for text in page_texts for char in text)
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
        operand = f"<{text.encode('utf-16-be').hex()}>" if unicode_font else f"({escaped})"
        content = f"BT /F1 12 Tf 72 720 Td {operand} Tj ET".encode() if text else b""
        objects.append(f"<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 {font_id} 0 R >> >> /MediaBox [0 0 612 792] /Contents {content_id} 0 R >>".encode())
        objects.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    if unicode_font:
        objects.append(f"<< /Type /Font /Subtype /Type0 /BaseFont /TrackTest /Encoding /Identity-H /DescendantFonts [{font_id + 1} 0 R] /ToUnicode {font_id + 2} 0 R >>".encode())
        objects.append(b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /TrackTest /CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> /DW 1000 >>")
        chars = sorted(set("".join(page_texts)))
        mappings = "\n".join(f"<{ord(c):04X}> <{c.encode('utf-16-be').hex()}>" for c in chars)
        cmap = ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
                "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
                "/CMapName /TrackTest-UCS def /CMapType 2 def\n"
                "1 begincodespacerange <0000> <FFFF> endcodespacerange\n"
                f"{len(chars)} beginbfchar\n{mappings}\nendbfchar\n"
                "endcmap CMapName currentdict /CMap defineresource pop end end").encode()
        objects.append(b"<< /Length %d >>\nstream\n" % len(cmap) + cmap + b"\nendstream")
    else:
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
        ("leading-empty", ["", "two"], b"\ftwo\f", [1]),
        ("middle-empty", ["one", "", "three"], b"one\f\fthree\f", [2]),
        ("trailing-empty", ["one", ""], b"one\f\f", [2]),
        ("printed-numbers", ["ix", "1"], b"ix\f1\f", []),
        ("japanese", ["売上高 1,200 百万円", "", "年度 2025"], "売上高 1,200 百万円\f\f年度 2025\f".encode(), [2]),
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
        assert metadata["extraction_method"].startswith("xberg 1.2.6 (native);")


def failure_cases(directory: Path) -> None:
    other_format = directory / "input.html"
    other_format.write_text("<p>not a PDF</p>", encoding="utf-8")
    other_output = directory / "other.txt"
    result = invoke(other_format, other_output)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "not_pdf"
    assert not other_output.exists() and not other_output.with_suffix(".original.pdf").exists()

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
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "xberg_failed"
    assert not (directory / "damaged.txt").exists()
    assert not (directory / "damaged.original.pdf").exists()

    existing = directory / "existing.txt"
    existing.write_text("keep", encoding="utf-8")
    result = invoke(image_only, existing)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "output_exists"
    assert existing.read_text(encoding="utf-8") == "keep"

    retained_output = directory / "retained.txt"
    retained_original = retained_output.with_suffix(".original.pdf")
    retained_original.write_bytes(b"keep original")
    result = invoke(image_only, retained_output)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "output_exists"
    assert retained_original.read_bytes() == b"keep original" and not retained_output.exists()


def consistency_and_timeout(directory: Path) -> None:
    tools = directory / "fake-xberg"
    tools.mkdir()
    fake = """#!/usr/bin/env python3
import json, os, pathlib, sys, time
marker = os.environ.get('FAKE_STARTED')
if marker:
    pathlib.Path(marker).touch()
time.sleep(float(os.environ.get('FAKE_DELAY', '0')))
data = pathlib.Path(sys.argv[1]).read_bytes()
result = {
    'engine': 'xberg 1.2.6 (native)',
    'page_count': int(os.environ.get('FAKE_PAGE_COUNT', '1')),
    'pages': [{'page_number': 1, 'content': 'first' if b'FIRST' in data else 'second'}],
    'warnings': [],
}
result.update(json.loads(os.environ.get('FAKE_FIELDS', '{}')))
print(os.environ.get('FAKE_RAW', json.dumps(result)))
print(os.environ.get('FAKE_WARNING', ''), end='', file=sys.stderr)
"""
    path = tools / "track-pdf-engine"
    path.write_text(textwrap.dedent(fake), encoding="utf-8")
    path.chmod(0o755)
    marker = directory / "xberg-started"
    environment = {
        **os.environ,
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
        "FAKE_DELAY": "0.3",
        "FAKE_STARTED": str(marker),
    }
    source = directory / "raced.pdf"
    first = b"%PDF-FIRST"
    source.write_bytes(first)
    output = directory / "raced.txt"
    process = subprocess.Popen(
        [sys.executable, str(SCRIPT), str(source), "--text-out", str(output), "--original-out", str(output.with_suffix('.original.pdf'))],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
    )
    deadline = time.monotonic() + 5
    while not marker.exists() and time.monotonic() < deadline:
        time.sleep(0.01)
    assert marker.exists(), "fake Xberg did not start"
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
        ("diagnostic", "FAKE_WARNING", "Syntax Warning", "xberg_diagnostic"),
        ("structured-warning", "FAKE_FIELDS", json.dumps({"warnings": [{"source": "pdf", "message": "dropped glyph"}]}), "xberg_diagnostic"),
        ("invalid-json", "FAKE_RAW", "not json", "invalid_engine_output"),
        ("mismatch", "FAKE_PAGE_COUNT", "2", "page_boundary_mismatch"),
        ("wrong-page", "FAKE_FIELDS", json.dumps({"pages": [{"page_number": 2, "content": "x"}]}), "page_boundary_mismatch"),
        ("missing-pages", "FAKE_FIELDS", json.dumps({"pages": None}), "page_boundary_mismatch"),
        ("form-feed", "FAKE_FIELDS", json.dumps({"pages": [{"page_number": 1, "content": "a\fb"}]}), "ambiguous_page_boundary"),
        ("boolean-count", "FAKE_FIELDS", json.dumps({"page_count": True}), "invalid_page_count"),
    ]:
        case_output = directory / f"{name}.txt"
        case_environment = {**environment, "FAKE_DELAY": "0", variable: value}
        result = invoke(source, case_output, env=case_environment)
        assert result.returncode == 1 and json.loads(result.stderr)["code"] == code
        assert not case_output.exists()
        assert not case_output.with_suffix(".original.pdf").exists()

    result = invoke(source, directory / "nan.txt", timeout=float("nan"), env=environment)
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "invalid_timeout"

    missing_output = directory / "missing-xberg.txt"
    result = invoke(source, missing_output, env={**os.environ, "PATH": ""})
    assert result.returncode == 1 and json.loads(result.stderr)["code"] == "xberg_missing"
    assert not missing_output.exists()

    collision = subprocess.run(
        [sys.executable, str(SCRIPT), str(source), "--text-out", str(source), "--original-out", str(directory / "copy.pdf")],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert collision.returncode == 1 and json.loads(collision.stderr)["code"] == "path_collision"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="track-clip-pdf-test-") as temporary:
        directory = Path(temporary)
        success_cases(directory)
        failure_cases(directory)
        consistency_and_timeout(directory)
    print("extract_pdf: all checks passed")


if __name__ == "__main__":
    main()
