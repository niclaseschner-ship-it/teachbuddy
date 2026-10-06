"""Wissenseinheiten lesen — die Eingabe des Podcast-Bauers (AUF-2).

Ein Format-Agent bekommt Wissenseinheiten samt Belegen und greift nicht
selbst auf Quellen oder die Bibliothek zu. Dieses Modul ist der Leser
dafür: Es macht aus Dateien die Liste, die `skript.py` in den Prompt gießt
und `belegprobe.py` gegenhält. Es kennt keinen Pfad in die Bibliothek und
soll keinen kennen.

`stand` ist der Hash der Datei. Ohne ihn ist AUF-9 (ein Artefakt kennt
seine Herkunft) nicht erfüllbar und BIB-20 (welche Artefakte sind nach
einer Korrektur veraltet?) nicht beantwortbar.
"""

import dataclasses
import hashlib
import os
import re

from bibliothek import yaml_min


FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)

# Ein Beleg heißt B-<quelle>-<nummer>, z. B. B-0002-01. Die Form ist der
# Vertrag zwischen Bibliothek und Format-Agent; belegprobe.py prüft gegen
# genau diesen Ausdruck.
BELEG_RE = re.compile(r"\AB-\d{4}-\d{2}\Z")


class EinheitFehler(Exception):
    """Eine Wissenseinheit ist nicht lesbar oder nicht vollständig."""


@dataclasses.dataclass(frozen=True)
class Wissenseinheit:
    id: str
    titel: str
    grad: str
    belege: tuple[str, ...]
    setzt_voraus: tuple[str, ...]
    inhalt: str
    stand: str

    @property
    def quellen(self) -> tuple[str, ...]:
        """Die Quellen-IDs hinter den Belegen (B-0002-01 → 0002)."""
        return tuple(sorted({b.split("-")[1] for b in self.belege}))


def _liste(wert, feld: str, datei: str) -> tuple[str, ...]:
    if wert is None:
        return ()
    if not isinstance(wert, list):
        raise EinheitFehler("%s: Feld %r ist keine Liste" % (datei, feld))
    return tuple(str(w).strip() for w in wert if str(w).strip())


def lies(pfad: str) -> Wissenseinheit:
    """Liest eine Wissenseinheit aus einer Markdown-Datei mit Frontmatter."""
    with open(pfad, encoding="utf-8") as f:
        roh = f.read()

    m = FRONTMATTER_RE.match(roh)
    if not m:
        raise EinheitFehler("%s: kein YAML-Frontmatter am Dateianfang" % pfad)
    # **Derselbe Leser wie die Bibliothek.** Bis zum 12.09.2026 stand hier
    # PyYAML, und die Bibliothek las mit `bibliothek.yaml_min`. Zwei Leser mit
    # verschiedener Toleranz heisst: eine Datei ist fuer den einen gueltig und
    # fuer den anderen nicht. In der Nacht ist genau das passiert — ein Titel
    # mit unmaskiertem Doppelpunkt ("... auf zwei Wegen: die Systeme ...") war
    # in der Bibliothek in Ordnung und liess die Vertonung von Abschnitt D
    # scheitern. Ein Leser, eine Wahrheit.
    try:
        kopf = yaml_min.lies_block(m.group(1), herkunft=pfad) or {}
    except yaml_min.YamlFehler as exc:
        raise EinheitFehler("%s: Frontmatter unlesbar (%s)" % (pfad, exc)) from exc
    if not isinstance(kopf, dict):
        raise EinheitFehler("%s: Frontmatter ist kein Block aus Feldern" % pfad)

    einheit_id = str(kopf.get("id") or "").strip()
    if not einheit_id:
        raise EinheitFehler("%s: Feld 'id' fehlt" % pfad)

    belege = _liste(kopf.get("belegt_durch"), "belegt_durch", pfad)
    if not belege:
        # Eine Einheit ohne Belege kann keinen Marker tragen, den die
        # Belegprobe auflöst — sie würde den Auftrag später scheitern
        # lassen. Lieber jetzt, mit Dateinamen.
        raise EinheitFehler("%s: Feld 'belegt_durch' ist leer (TB-1)" % pfad)
    for beleg in belege:
        if not BELEG_RE.match(beleg):
            raise EinheitFehler(
                "%s: Beleg %r hat nicht die Form B-nnnn-nn" % (pfad, beleg))

    return Wissenseinheit(
        id=einheit_id,
        titel=str(kopf.get("titel") or "").strip(),
        grad=str(kopf.get("grad") or "").strip(),
        belege=belege,
        setzt_voraus=_liste(kopf.get("setzt_voraus"), "setzt_voraus", pfad),
        inhalt=m.group(2).strip(),
        stand=hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16],
    )


def lies_verzeichnis(pfad: str,
                     nur: "list[str] | None" = None) -> list[Wissenseinheit]:
    """Liest alle `*.md` eines Verzeichnisses, sortiert nach ID.

    `nur` schneidet die Lektion zu (POD-3): Eine Folge ist eine Lektion,
    und der Zuschnitt ist die Zeitspanne, nicht der Inhalt eines Ordners.
    Solange es keine Lektionsgrenzen in der Bibliothek gibt, wird die
    Auswahl von Hand übergeben.
    """
    if not os.path.isdir(pfad):
        raise EinheitFehler("%s ist kein Verzeichnis" % pfad)
    dateien = sorted(n for n in os.listdir(pfad) if n.endswith(".md"))
    if not dateien:
        raise EinheitFehler("%s enthält keine Wissenseinheiten" % pfad)
    einheiten = [lies(os.path.join(pfad, n)) for n in dateien]
    if nur:
        gewuenscht = list(dict.fromkeys(nur))
        vorhanden = {e.id: e for e in einheiten}
        fehlend = [i for i in gewuenscht if i not in vorhanden]
        if fehlend:
            raise EinheitFehler(
                "%s: Einheiten nicht gefunden: %s" % (pfad, ", ".join(fehlend)))
        einheiten = [vorhanden[i] for i in gewuenscht]
    einheiten.sort(key=lambda e: e.id)
    return einheiten


def belegregister(einheiten: list[Wissenseinheit]) -> dict[str, list[str]]:
    """Beleg-ID → die übergebenen Einheiten, die auf ihr stehen.

    Das ist das Nachschlagewerk der Belegprobe (AUF-8b): Ein Marker ist
    genau dann auflösbar, wenn er hier einen Eintrag hat.
    """
    register: dict[str, list[str]] = {}
    for einheit in einheiten:
        for beleg in einheit.belege:
            register.setdefault(beleg, []).append(einheit.id)
    return register
