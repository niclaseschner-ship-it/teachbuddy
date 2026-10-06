#!/usr/bin/env bash
# Malt das Titelbild einer Lektion über die Codex-CLI (ChatGPT-Abo, kein
# API-Schlüssel) und bindet es in die Bibliothek ein (E-19d).
#
#   pipeline/lektionsbild/bauen.sh L-S2
#
# Codex schreibt zuerst die Strukturanalyse und den Bildauftrag
# (analyse-auftrag.md), dann malt es mit dem eingebauten image_gen
# (mal-auftrag.md). Das Bild bitte ansehen, bevor es veröffentlicht wird:
# Schreibfehler und dunkle Schleier rutschen gelegentlich durch.
set -euo pipefail
ID=${1:?Lektion angeben, z. B. L-S2}
HIER=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HIER/../.." && pwd)
PY=${PYTHON:-python3}
cd "$REPO"
ARBEIT=$("$PY" -c 'import pfade; print(pfade.ARBEIT)')/lektionsbild/$ID
CODEX=${TEACHBUDDY_CODEX:-codex}
FRIST=""; command -v timeout >/dev/null && FRIST="timeout 900"

rm -rf "$ARBEIT"; mkdir -p "$ARBEIT"
"$PY" -m pipeline.lektionsbild.material "$ID" > "$ARBEIT/material.md"
cd "$ARBEIT"
# </dev/null: ohne das wartet codex exec auf weitere Eingabe.
$FRIST "$CODEX" exec --sandbox workspace-write --skip-git-repo-check \
  "$(cat "$HIER/analyse-auftrag.md")" < /dev/null > analyse.log 2>&1 || true
[ -s bildprompt.txt ] || { echo "$ID: kein Bildauftrag entstanden (siehe $ARBEIT/analyse.log)"; exit 1; }
$FRIST "$CODEX" exec --sandbox workspace-write --skip-git-repo-check \
  "$(cat "$HIER/mal-auftrag.md")" < /dev/null > mal.log 2>&1 || true
if [ ! -f bild.png ]; then
  # Das Werkzeug legt Bilder unter $CODEX_HOME ab; vergisst Codex das Kopieren,
  # wird das neueste von dort geholt.
  neu=$(find "${CODEX_HOME:-$HOME/.codex}/generated_images" -name '*.png' -newer bildprompt.txt 2>/dev/null | sort | tail -1 || true)
  [ -n "$neu" ] && cp "$neu" bild.png
fi
[ -f bild.png ] || { echo "$ID: kein Bild entstanden (siehe $ARBEIT/mal.log)"; exit 1; }
cd "$REPO"
"$PY" -m pipeline.lektionsbild.einbinden "$ID"
