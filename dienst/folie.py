"""Aus dem Inhalt einer Wissenseinheit die Folienpunkte lesen (R-6, BIB-11).

`folie_url` ist mit Datenvertrag v2 entfallen; ``folie_punkte`` ist die
Wahrheit der Folie. Die Punkte werden nicht erfunden, sondern **abgelesen**:
Das Material markiert jede Aussage mit ihren Belegen (``[B-0002-01]``) und
jede Einordnung mit ``[E]`` — genau die Unterscheidung, die BIB-11 verlangt
und die der Vertrag als ``art`` fuehrt.

Was hier bewusst **nicht** entsteht: ``art: "strittig"``. Dafuer gibt es im
Material kein Merkmal (siehe Befund ``strittig_ohne_feld``). Eine Aussage als
strittig auszugeben, weil im Text das Wort vorkommt, waere geraten.
"""

from __future__ import annotations

import re
from typing import Any

__all__ = ["BELEG_MARKE", "folie_punkte"]

BELEG_MARKE = re.compile(r"\[(B-\d{4}-\d{2})\]")
_EINORDNUNG = re.compile(r"\s*\[E\]\s*")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_ABSATZ = re.compile(r"\n\s*\n")


def folie_punkte(inhalt: str) -> list[dict[str, Any]]:
    """Zerlegt den Inhalt einer Wissenseinheit in Folienpunkte."""
    punkte: list[dict[str, Any]] = []
    for roh in _ABSATZ.split(inhalt or ""):
        absatz = roh.strip()
        if not absatz:
            continue
        # `[E]` steht am Anfang oder hinter dem Satz, den es kennzeichnet. Ein
        # Absatz mit `[E]` und ohne Beleg ist eine Einordnung; einer ganz ohne
        # Marke bleibt unbelegt (BIB-11) und wird nicht zur Einordnung erklaert.
        fuehrt_mit_e = absatz.startswith("[E]")
        einordnung = bool(_EINORDNUNG.search(absatz))
        absatz = _EINORDNUNG.sub(" ", absatz).strip()
        belege = list(dict.fromkeys(BELEG_MARKE.findall(absatz)))
        text = BELEG_MARKE.sub("", absatz)
        text = _WIKILINK.sub(r"\1", text)
        text = re.sub(r"\s+([.,;:])", r"\1", text)
        text = re.sub(r"[ \t]*\n[ \t]*", " ", text)
        text = re.sub(r"\s{2,}", " ", text).strip()
        if not text:
            continue
        if fuehrt_mit_e:
            art = "einordnung"          # ausdruecklich als Ganzes eingeordnet
        elif belege:
            art = "belegt"
        elif einordnung:
            art = "einordnung"
        else:
            # BIB-11: Eine inhaltliche Aussage ohne Beleg ist als Einordnung zu
            # kennzeichnen. Steht sie unmarkiert da, ist das ein Mangel am
            # Material — er wird sichtbar gemacht, nicht geglaettet.
            art = "unbelegt"
        punkte.append({"text": text, "belege": belege, "art": art})
    return punkte
