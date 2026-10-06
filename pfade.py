"""Wo TeachBuddy seine Dateien findet — und woher es seine Einstellungen liest.

Drei Orte, jeder per Umgebungsvariable umstellbar:

``TEACHBUDDY_WISSEN``  die Bibliothek: Lernpfade, Kapitel, Wissenseinheiten,
                       Belege, Bilder und Audio (Standard: ``demo/``)
``TEACHBUDDY_ARBEIT``  was gebaut oder gemessen wird: Index, Lernstand,
                       Kosten, Zwischenstände der Pipeline (Standard: ``arbeit/``)
``TEACHBUDDY_INDEX``   der SQLite-Index (Standard: ``<ARBEIT>/index.db``)

Pfade in der Bibliothek (``bild:``, ``audio:``) sind relativ zu ``WISSEN``.
Eine Bibliothek lässt sich damit verschieben oder austauschen, ohne dass sich
ihre Dateien ändern.

Beim Import wird ``.env`` im Projektordner gelesen, falls vorhanden. Schon
gesetzte Umgebungsvariablen haben Vorrang.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parent


def lade_env(datei: Path = REPO / ".env") -> None:
    """Liest ``KEY=WERT``-Zeilen aus ``.env``, ohne Gesetztes zu überschreiben."""
    if not datei.is_file():
        return
    for zeile in datei.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        name, wert = zeile.split("=", 1)
        wert = wert.strip().strip('"').strip("'")
        if wert:
            os.environ.setdefault(name.strip(), wert)


lade_env()


def _pfad(variable: str, standard: Path) -> Path:
    wert = os.environ.get(variable)
    return Path(wert).expanduser().resolve() if wert else standard


WISSEN = _pfad("TEACHBUDDY_WISSEN", REPO / "demo")
ARBEIT = _pfad("TEACHBUDDY_ARBEIT", REPO / "arbeit")
INDEX = _pfad("TEACHBUDDY_INDEX", ARBEIT / "index.db")
PODCAST_ARBEIT = ARBEIT / "podcast"


def in_wissen(relativ: str) -> Path | None:
    """Löst einen Pfad aus der Bibliothek auf — nie über ``WISSEN`` hinaus."""
    datei = (WISSEN / relativ).resolve()
    return datei if datei.is_relative_to(WISSEN) else None
