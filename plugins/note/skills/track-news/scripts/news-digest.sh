#!/usr/bin/env bash
# news-digest.sh — track-news の新着ダイジェスト乾燥ラン(draft)
#
# 役割: vault から新着の自動生成記事(共通タグ付き)を発見し、newsダイジェストの
#       見出し+襟のテキストを生成して stdout に出す。journal への書き込みはしない。
#
# 使い方:
#   TRACK_VAULT=/path/to/vault ./news-digest.sh --tag auto --limit 10
#   ./news-digest.sh --tag auto --date 2026-09-06   # 指定日の活動ノートに絞る(要 track agenda)
#
# 依存: track CLI, jq。track は PATH にあるか TRACK_BIN で指定。
set -euo pipefail

TRACK_BIN="${TRACK_BIN:-track}"
TAG="auto"
LIMIT="10"
DATE=""

usage() {
  sed -n '2,12p' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tag)   TAG="$2"; shift 2 ;;
    --limit) LIMIT="$2"; shift 2 ;;
    --date)  DATE="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

[[ -n "${TRACK_VAULT:-}" ]] || { echo "TRACK_VAULT is required" >&2; exit 2; }

run() { TRACK_VAULT="$TRACK_VAULT" "$TRACK_BIN" "$@"; }

# 1) ノート一覧(newest first, journal除外)。tags に共通タグを含むものを上限まで拾う。
list_json="$(run notes)"
echo "$list_json" | jq -r --arg tag "$TAG" '
  .notes[]
  | select((.tags // []) | index($tag))
  | [.note_id, .title, (.tags // [] | join(","))]
  | @tsv
' | head -n "$LIMIT" > /tmp/track-news.$$.tsv || true

if [[ ! -s /tmp/track-news.$$.tsv ]]; then
  echo "no notes tagged #${TAG}" >&2
  rm -f /tmp/track-news.$$.tsv
  exit 0
fi

# 2) 各ノートの description を meta で引いて襟にする。無ければ 2 行目以降の要約を
#    漢字で入れず「(descriptionなし)」ではなく本文からは掘らない(dry-run なので簡略)。
echo "## News"
while IFS=$'\t' read -r id title tags; do
  desc="$(run meta --id "$id" 2>/dev/null | jq -r '.description // empty')"
  if [[ -n "$desc" ]]; then
    echo "- [[${title}]] — ${desc}"
  else
    echo "- [[${title}]]"
  fi
done < /tmp/track-news.$$.tsv

rm -f /tmp/track-news.$$.tsv
