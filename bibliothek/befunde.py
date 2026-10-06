"""Was am Material auffällt — die Befunde des Index, nach Art gruppiert.

    python -m bibliothek.befunde                 # Übersicht
    python -m bibliothek.befunde absatz_ohne_marker   # eine Art ausführlich

Fehler verhindern nichts, aber sie gehören vor die Freigabe behoben.
Abweichungen sind bekannt und meist harmlos; `absatz_ohne_marker` dagegen
heißt: Ein Absatz steht ohne Beleg und ohne `[E]` auf der Folie (BIB-11).
"""
from __future__ import annotations

import sys
from collections import Counter

import pfade
from bibliothek import abfragen
from bibliothek.index import baue_index, oeffne


def main(argv: list[str]) -> int:
    baue_index(pfade.WISSEN, pfade.INDEX)
    alle = abfragen.befunde(oeffne(pfade.INDEX))
    if argv:
        for f in (f for f in alle if f["art"] == argv[0]):
            print(f"{f['betrifft']:12} {f['text']}")
        return 0
    zaehler = Counter((f["schwere"], f["art"]) for f in alle)
    for (schwere, art), n in sorted(zaehler.items()):
        print(f"  {schwere:11} {art:32} {n:4}")
    fehler = sum(n for (s, _), n in zaehler.items() if s == "fehler")
    print(f"\n  {len(alle)} Befunde, davon {fehler} Fehler ({pfade.WISSEN})")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
