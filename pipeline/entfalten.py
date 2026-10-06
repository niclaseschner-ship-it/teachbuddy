"""Entfaltet ein Agentenbündel in einzelne Dateien.

**Warum es das gibt.** Am 12.09.2026 gemessen, an einem echten Lauf:

    Bash 88 · Edit 32 · Write 18 · WebSearch 7 · Read 4

Sieben Aufrufe waren Recherche, 138 waren Dateien hin- und herschieben. Weil
jeder Werkzeugaufruf den ganzen Kontext erneut liest (150 000 Token), zahlen
wir fast die gesamten zehn Millionen Token je Lauf für Fleißarbeit.

Der Agent schreibt deshalb **eine** Datei mit allem darin, und dieses Skript
zerlegt sie. Aus 138 mechanischen Aufrufen werden zwei.

Format, bewusst dumm gehalten, damit ein Modell es fehlerfrei trifft::

    <<<DATEI belege/B-0019-01.md>>>
    ---
    id: B-0019-01
    ---
    Text …
    <<<DATEI einheiten/WE-0042.md>>>
    ---
    id: WE-0042
    ---
    …

Das Skript **normalisiert** dabei, statt dem Modell Sorgfalt abzuverlangen:
Ein Kopfwert mit ``: `` bekommt Anführungszeichen. Genau daran ist am
12.09.2026 die Vertonung von Abschnitt D gescheitert.

Aufruf::

    python3 -m pipeline.entfalten <buendel.md> <zielwurzel>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

MARKE = re.compile(r"^<<<DATEI\s+(.+?)\s*>>>\s*$", re.M)

# Werte, die ein ": " enthalten, muessen in Anfuehrungszeichen. Listen,
# Abbildungen und bereits zitierte Werte bleiben unangetastet.
_ROH = ("[", "{", '"', "'", ">", "|")


def _kopf_normalisieren(kopf: str) -> tuple[str, list[str]]:
    raus, notizen = [], []
    for zeile in kopf.split("\n"):
        m = re.match(r"^([a-z_][a-z0-9_]*):\s(.+)$", zeile)
        if m and ": " in m.group(2) and not m.group(2).lstrip().startswith(_ROH):
            wert = m.group(2).strip().replace('"', "'")
            raus.append(f'{m.group(1)}: "{wert}"')
            notizen.append(f"{m.group(1)} in Anfuehrungszeichen gesetzt (Doppelpunkt im Wert)")
        else:
            raus.append(zeile)
    return "\n".join(raus), notizen


def entfalten(buendel: Path, wurzel: Path) -> tuple[int, list[str]]:
    text = buendel.read_text(encoding="utf-8")
    marken = list(MARKE.finditer(text))
    if not marken:
        raise SystemExit(f"{buendel}: keine <<<DATEI …>>>-Marke gefunden.")

    wurzel = wurzel.resolve()
    geschrieben, notizen = 0, []
    for nr, m in enumerate(marken):
        ende = marken[nr + 1].start() if nr + 1 < len(marken) else len(text)
        inhalt = text[m.end():ende].strip("\n") + "\n"

        ziel = (wurzel / m.group(1)).resolve()
        # Nichts ausserhalb der Wurzel. Ein Buendel ist Modellausgabe, und
        # Modellausgabe darf nicht bestimmen, wohin geschrieben wird.
        if not str(ziel).startswith(str(wurzel) + "/"):
            raise SystemExit(f"{m.group(1)} zeigt aus der Zielwurzel heraus.")

        k = re.match(r"^---\n(.*?)\n---\n(.*)$", inhalt, re.S)
        if k:
            kopf, hinweise = _kopf_normalisieren(k.group(1))
            notizen += [f"{ziel.name}: {h}" for h in hinweise]
            inhalt = f"---\n{kopf}\n---\n{k.group(2)}"

        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
        geschrieben += 1
    return geschrieben, notizen


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    n, notizen = entfalten(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"{n} Dateien geschrieben")
    for x in notizen:
        print("  berichtigt:", x)
