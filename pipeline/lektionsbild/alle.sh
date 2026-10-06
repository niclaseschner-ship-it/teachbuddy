#!/usr/bin/env bash
# Malt die Bilder aller Lektionen, die noch keins haben — einzeln nacheinander
# (AUF-10). Ist das Codex-Kontingent leer, hält der Lauf an, statt jede weitere
# Lektion in Sekunden scheitern zu lassen.
#
#   pipeline/lektionsbild/alle.sh            # alle ohne Bild
#   pipeline/lektionsbild/alle.sh L-S1 L-S2  # nur diese
HIER=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HIER/../.." && pwd)
PY=${PYTHON:-python3}
cd "$REPO"
ARBEIT=$("$PY" -c 'import pfade; print(pfade.ARBEIT)')/lektionsbild
LISTE=("$@")
[ ${#LISTE[@]} -eq 0 ] && read -r -a LISTE <<< "$("$PY" -m pipeline.lektionsbild.material --ohne-bild)"
for id in "${LISTE[@]}"; do
  s=$(date +%s)
  if "$HIER/bauen.sh" "$id" >/dev/null 2>&1; then e=ok; else e=FEHLT; fi
  echo "$(date +%H:%M) $id $e $(( $(date +%s) - s ))s"
  if grep -qh "usage limit" "$ARBEIT/$id"/*.log 2>/dev/null; then
    echo "ABBRUCH: Codex-Kontingent leer — $(grep -oh 'try again at [^.]*' "$ARBEIT/$id"/*.log | tail -1)"
    exit 1
  fi
done
