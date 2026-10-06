"""Prüft einen Rechercheertrag maschinell.

**Warum es das gibt.** Am 12.09.2026 hat zum ersten Mal Haiku recherchiert.
Die Fundstellen waren echt und wörtlich zitiert — aber ein Beleg zeigte auf
`F-0005-01`, während seine Aussage aus `F-0001-02` stammte. Ein falscher
Verweis sieht genauso aus wie ein richtiger, solange niemand nachschlägt.

Und genau darin liegt die Bedingung, unter der ein kleines Modell diese
Arbeit machen darf: **Wo sich das Ergebnis mechanisch prüfen lässt, ist ein
Fehler kein Risiko, sondern ein Befund.** Ohne diese Probe ist die Ersparnis
nichts wert, weil sie mit unbemerkt falschen Belegen bezahlt wird.

Geprüft wird, was ohne Urteil entscheidbar ist:

1. Jeder Beleg nennt eine Fundstelle, und es gibt sie.
2. Beleg und Fundstelle gehören zur selben Quelle (B-0011-* → F-0011-*).
3. Jede Fundstelle trägt ein nichtleeres Zitat (BIB-8: wörtlich, nicht
   umschrieben).
4. Jede Fundstelle nennt eine Quellenversion, und es gibt sie.
5. Keine Quelle, keine Fundstelle, kein Beleg überschreibt etwas, das
   anderswo in der Bibliothek schon existiert.

Nicht geprüft wird, ob die Deutung trägt. Das ist ein Urteil und bleibt beim
Menschen (BIB-16).

Aufruf::

    python3 -m pipeline.belegprobe <eingangsordner>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pfade  # noqa: E402

WISSEN = pfade.WISSEN


def _feld(text: str, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+?)\s*$", text, re.M)
    return (m.group(1).strip().strip("\"'") if m else "")


def pruefe(ordner: Path) -> list[str]:
    klagen: list[str] = []

    fundstellen: dict[str, str] = {}      # F-ID → Zitat
    versionen: set[str] = set()
    for datei in ordner.glob("quellen/*/versionen/*.md"):
        versionen.add(datei.stem)
    for datei in ordner.glob("quellen/*/fundstellen.md"):
        text = datei.read_text(encoding="utf-8")
        for block in re.split(r"^##\s+(F-[\d-]+)\s*$", text, flags=re.M)[1:]:
            pass
        teile = re.split(r"^##\s+(F-[\d-]+)\s*$", text, flags=re.M)
        for fid, inhalt in zip(teile[1::2], teile[2::2]):
            zitat = ""
            m = re.search(r"^zitat:\s*(?:>\s*\n((?:\s+.+\n?)+)|(.+))$", inhalt, re.M)
            if m:
                zitat = (m.group(1) or m.group(2) or "").strip()
            fundstellen[fid] = zitat
            if not zitat:
                klagen.append(f"{fid}: kein Zitat — eine Fundstelle ohne Wortlaut "
                              "ist keine (BIB-8)")
            v = _feld(inhalt, "version")
            if v and versionen and v not in versionen:
                klagen.append(f"{fid}: nennt Version {v}, die es hier nicht gibt")

    for datei in sorted(ordner.glob("belege/*.md")):
        text = datei.read_text(encoding="utf-8")
        bid = _feld(text, "id") or datei.stem
        fid = _feld(text, "fundstelle")
        if not fid:
            klagen.append(f"{bid}: nennt keine Fundstelle (TB-1)")
            continue
        if fid not in fundstellen:
            klagen.append(f"{bid}: zeigt auf {fid}, die es nicht gibt")
            continue
        qb = re.match(r"B-(\d+)-", bid)
        qf = re.match(r"F-(\d+)-", fid)
        if qb and qf and qb.group(1) != qf.group(1):
            klagen.append(f"{bid}: gehoert zu Quelle {qb.group(1)}, zeigt aber auf "
                          f"{fid} aus Quelle {qf.group(1)}")

    # Nichts ueberschreiben, was anderswo schon liegt
    for muster, was in (("quellen/Q-*", "Quelle"), ("belege/*.md", "Beleg")):
        for datei in ordner.glob(muster):
            fremd = [d for d in WISSEN.glob(f"eingang/*/{muster}")
                     if d.name == datei.name and d.parent.parent != ordner
                     and ordner not in d.parents]
            if fremd:
                klagen.append(f"{was} {datei.name} gibt es schon in "
                              f"{fremd[0].parent.parent.name}")
    return klagen


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    ordner = Path(sys.argv[1])
    klagen = pruefe(ordner)
    belege = len(list(ordner.glob("belege/*.md")))
    quellen = len(list(ordner.glob("quellen/Q-*")))
    print(f"{ordner.name}: {quellen} Quellen, {belege} Belege")
    if not klagen:
        print("  URTEIL sauber")
        raise SystemExit(0)
    print(f"  URTEIL {len(klagen)} Befunde")
    for k in klagen[:30]:
        print("   ·", k)
    raise SystemExit(1)
