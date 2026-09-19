"""Offline CLI rehearsal in a temporary vault; never writes the user's vault.

Run: python3 scripts/check-knowledge-intake.py /absolute/path/to/track
Checks storage primitives and fixed search cases, not model answer quality.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


with tempfile.TemporaryDirectory(prefix="track-intake-") as directory:
    env = {key: value for key, value in os.environ.items() if not key.startswith("TRACK_")}
    env.update(TRACK_CONFIG=str(Path(directory) / "config.yml"),
               TRACK_VAULT=str(Path(directory) / "vault"), TRACK_CACHE_DIR=str(Path(directory) / "cache"))
    binary = str(Path(sys.argv[1]).resolve(strict=True))

    def track(*args):
        result = subprocess.run([binary, *map(str, args)], env=env, text=True, capture_output=True)
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout if args[0] == "export" else json.loads(result.stdout)

    def new(title, body):
        track("new", "--title", title, "--body", body)
        return track("resolve", "--term", title)["note_id"]

    track("init")
    source = "https://example.invalid/article?edition=1"
    old = "## 根拠\n値は10。\n"
    changed = "## 根拠\n値は12。\n"
    digest = hashlib.sha256(old.encode()).hexdigest()
    first = new("資料", f"[Source]({source})\nsha256: {digest}\n取得: 2026-09-18T09:00:00+09:00\n\n{old}")
    # Rehearse interruption between body creation and metadata write: recover the same ID.
    before = track("export", "--id", first)
    assert digest in before and source in before
    track("meta", "--id", first, "--set", f"source-url={source}",
          "--set", f"content-sha256={digest}", "--set", "retrieved-at=2026-09-18T09:00:00+09:00",
          "--set", "content-format=text/markdown", "--set", "extraction-method=fixture")
    assert track("resolve", "--term", "資料")["note_id"] == first
    assert digest in json.dumps(track("meta", "--id", first))
    second_digest = hashlib.sha256(changed.encode()).hexdigest()
    second_title = f"資料 — sha256-{second_digest}"
    second = new(second_title, changed)
    assert second != first
    assert track("resolve", "--term", second_title)["note_id"] == second
    assert track("export", "--id", first) == before
    report = new("回答", "値は10。[^1]\n\n[^1]: [元資料](" + source + ")、[[資料#根拠]]、sha256: " + digest)
    assert "値は10" in track("export", "--id", report)
    assert "## 根拠" in track("export", "--id", first)
    assert not track("resolve", "--term", "存在しない資料")["found"]

    expected_cache = {new("Cache 設計", "## TTL\nTTL は60秒。"),
                      new("Cache 訂正", "## TTL\n旧仕様に反して TTL は30秒。")}
    new("長い運用ログ", "Cache を参照。\n" + "通常運用のログ。\n" * 100)
    retry = new("取得記録", "## 復旧\nretry は失敗項目のみ。")
    capacity = {new(f"容量 {i}", f"## 容量\n上限{i}件。") for i in range(6)}

    def measure(query, expected, bounded):
        searches = 1
        if bounded:
            candidates = track("search", "--scope", "title", "--query", query, "--limit", 20)["results"]
            if not candidates:
                searches += 1
                candidates = track("search", "--scope", "body", "--query", query, "--limit", 20)["results"]
            candidates = candidates[:5]
        else:
            candidates = track("search", "--query", query, "--limit", 20)["results"]
        ids = {row["note_id"] for row in candidates}
        bodies = [track("export", "--id", note_id) for note_id in ids]
        return {"searches": searches, "opened": len(ids), "characters": sum(map(len, bodies)),
                "missed": len(expected - ids)}

    comparisons = {}
    for query, expected in [("Cache", expected_cache), ("retry", {retry}), ("容量", capacity)]:
        comparisons[query] = {"baseline": measure(query, expected, False),
                              "bounded": measure(query, expected, True)}
    assert comparisons["Cache"]["bounded"]["missed"] == 0  # Conflicting evidence retained.
    assert comparisons["Cache"]["bounded"]["characters"] < comparisons["Cache"]["baseline"]["characters"]
    assert comparisons["retry"]["bounded"]["missed"] == 0  # Body fallback.
    assert comparisons["容量"]["bounded"]["missed"] == 1  # Limit is not exhaustive coverage.

    # Fixed half-open interval with equivalent timezone representations.
    from datetime import datetime
    start = datetime.fromisoformat("2026-09-18T00:00:00+09:00")
    end = datetime.fromisoformat("2026-09-19T00:00:00+09:00")
    times = ["2026-09-17T14:59:59+00:00", "2026-09-17T15:00:00+00:00",
             "2026-09-18T23:59:59+09:00", "2026-09-18T15:00:00+00:00"]
    assert [start <= datetime.fromisoformat(t) < end for t in times] == [False, True, True, False]
    print(json.dumps({"storage": "passed", "period_boundary": "passed", "search": comparisons}, ensure_ascii=False))
