"""Baut ``index.db`` aus den Dateien (BIB-18b).

Der Index ist **Wegwerfware**. Er wird immer komplett neu gebaut, nie
inkrementell, nie von Hand geaendert und liegt nicht im Git. Geht er kaputt,
wird er weggeworfen und neu gebaut.

Gebaut wird in eine Nebendatei und am Ende per ``os.replace`` an den Platz
geschoben — ein abgebrochener Bau laesst den alten Index stehen, statt einen
halben zu hinterlassen.

Aufruf::

    python -m bibliothek.index                       # Bibliothek -> arbeit/index.db
    python -m bibliothek.index --wissen pfad/zur/bibliothek --ziel pfad/index.db
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import json
import sqlite3
import sys
import threading
from pathlib import Path

from .lesen import BIB22_TYPEN, Bibliothek, lies_bibliothek

__all__ = ["SCHEMA", "IndexJeStrang", "baue_index", "oeffne"]

SCHEMA = """
CREATE TABLE quellen (
    id                    TEXT PRIMARY KEY,
    titel                 TEXT NOT NULL,
    urheber               TEXT,
    art                   TEXT,
    fundort               TEXT,
    veroeffentlicht       TEXT,
    abgerufen             TEXT,
    lizenz                TEXT,
    qualitaet             TEXT,
    qualitaet_begruendung TEXT,
    reichweite            TEXT,
    reichweite_detail     TEXT,
    anmerkung             TEXT,
    herkunft              TEXT NOT NULL,
    freigegeben           INTEGER NOT NULL,
    pfad                  TEXT NOT NULL
);

CREATE TABLE versionen (
    schluessel  TEXT PRIMARY KEY,   -- '<quelle>/<version>', siehe BIB-4a-Befund
    id          TEXT NOT NULL,
    quelle_id   TEXT NOT NULL REFERENCES quellen(id),
    zeichen     INTEGER NOT NULL,
    herkunft    TEXT NOT NULL,
    pfad        TEXT NOT NULL
);
CREATE INDEX versionen_quelle ON versionen(quelle_id);

CREATE TABLE fundstellen (
    id          TEXT PRIMARY KEY,
    quelle_id   TEXT NOT NULL REFERENCES quellen(id),
    version_id  TEXT,
    schluessel  TEXT,               -- '<quelle>/<version>'
    stelle      TEXT,
    zitat       TEXT NOT NULL,
    anmerkung   TEXT,
    herkunft    TEXT NOT NULL,
    freigegeben INTEGER NOT NULL,
    pfad        TEXT NOT NULL
);
CREATE INDEX fundstellen_quelle ON fundstellen(quelle_id);

CREATE TABLE belege (
    id            TEXT PRIMARY KEY,
    fundstelle_id TEXT REFERENCES fundstellen(id),
    gilt_ab       TEXT,
    zuversicht    TEXT,
    aussage       TEXT NOT NULL,
    begruendung   TEXT,
    herkunft      TEXT NOT NULL,
    freigegeben   INTEGER NOT NULL,
    pfad          TEXT NOT NULL
);
CREATE INDEX belege_fundstelle ON belege(fundstelle_id);

CREATE TABLE einheiten (
    id          TEXT PRIMARY KEY,
    titel       TEXT NOT NULL,
    stichwort   TEXT,
    grad        TEXT,
    kurzfassung TEXT,
    inhalt      TEXT,
    prueffrage  TEXT,
    gilt_ab     TEXT,
    herkunft    TEXT NOT NULL,
    freigegeben INTEGER NOT NULL,
    pfad        TEXT NOT NULL
);

CREATE TABLE pfade (
    id          TEXT PRIMARY KEY,
    reihenfolge INTEGER NOT NULL DEFAULT 99,
    titel       TEXT NOT NULL,
    kurzfassung TEXT,
    status      TEXT,
    sprache     TEXT,
    pfad        TEXT NOT NULL
);

CREATE TABLE abschnitte (
    pfad_id    TEXT NOT NULL REFERENCES pfade(id),
    schluessel TEXT NOT NULL,
    nummer     INTEGER NOT NULL,
    titel      TEXT NOT NULL,
    kern       TEXT,
    text       TEXT,
    PRIMARY KEY (pfad_id, schluessel)
);

-- Die Lektionsschicht aus BIB-26/27. Sie hat im Material noch keine
-- Dateiform; die Tabellen bleiben leer, bis es Lektionsdateien gibt. Sie
-- stehen hier, weil der Datenvertrag v2 sie verlangt und der Dienst sonst
-- an zwei Stellen raten muesste, statt an einer ehrlich leer zu sein.
CREATE TABLE lektionen (
    id         TEXT PRIMARY KEY,
    pfad_id    TEXT,
    kapitel    TEXT,
    abschnitt  TEXT,
    nummer     INTEGER,
    titel      TEXT,
    dauer_sek  INTEGER,
    audio_pfad TEXT
);
-- BIB-26: Die Ebene zwischen Lernpfad und Lektion. Sie traegt Mindmap und
-- Gespraechspartner; die dreizehn Abschnitte darunter sind Lektionen.
CREATE TABLE kapitel (
    id          TEXT PRIMARY KEY,
    pfad_id     TEXT,
    nummer      INTEGER,
    titel       TEXT,
    kurzfassung TEXT,
    pfad        TEXT NOT NULL
);
CREATE TABLE kapitel_lektionen (
    kapitel_id TEXT NOT NULL REFERENCES kapitel(id),
    abschnitt  TEXT NOT NULL,
    rang       INTEGER NOT NULL,
    PRIMARY KEY (kapitel_id, abschnitt)
);
CREATE TABLE lektion_einheiten (
    lektion_id TEXT NOT NULL REFERENCES lektionen(id),
    einheit_id TEXT NOT NULL REFERENCES einheiten(id),
    rang       INTEGER NOT NULL,
    PRIMARY KEY (lektion_id, einheit_id)
);
-- E-19a: Die Strukturanalyse je Kapitel. Sie ist Daten, kein Bild — die
-- Mindmap bleibt eine Ansicht (MMP-8), diese Tabellen geben ihr die
-- Gliederung, nach der sie zeichnet.
CREATE TABLE mindmap_analyse (
    kapitel     TEXT PRIMARY KEY,
    kern        TEXT,
    kernaussage TEXT,
    beziehungen TEXT,
    layout      TEXT,
    pfad        TEXT NOT NULL,
    bild        TEXT,
    bild_breite INTEGER,
    bild_hoehe  INTEGER,
    bild_titel  TEXT,
    bild_belege TEXT
);
-- MMP-10a: `eltern` ist gesetzt, wenn die Analyse zwei Ebenen hat.
CREATE TABLE mindmap_achsen (
    kapitel  TEXT NOT NULL REFERENCES mindmap_analyse(kapitel),
    achse_id TEXT NOT NULL,
    rang     INTEGER NOT NULL,
    frage    TEXT,
    eltern       TEXT,
    eltern_frage TEXT,
    PRIMARY KEY (kapitel, achse_id)
);
CREATE TABLE mindmap_achse_einheiten (
    kapitel    TEXT NOT NULL,
    achse_id   TEXT NOT NULL,
    einheit_id TEXT NOT NULL REFERENCES einheiten(id),
    rang       INTEGER NOT NULL,
    PRIMARY KEY (kapitel, achse_id, einheit_id)
);
-- R-10: Eine Marke traegt ihre Bedeutung in `art`, nicht im Titeltext.
CREATE TABLE kapitelmarken (
    lektion_id TEXT NOT NULL REFERENCES lektionen(id),
    sek        INTEGER NOT NULL,
    titel      TEXT,
    art        TEXT,
    PRIMARY KEY (lektion_id, sek)
);
CREATE TABLE lektion_zusatz (
    lektion_id      TEXT PRIMARY KEY REFERENCES lektionen(id),
    auftrag         TEXT,
    zeichen_vertont INTEGER,
    stimmen         TEXT,
    erzeugt         TEXT,
    bild            TEXT,
    bild_breite     INTEGER,
    bild_hoehe      INTEGER,
    bild_titel      TEXT,
    bild_belege     TEXT,
    -- AUF-18a: Fassung der Podcast-Pipeline. NULL bei allem vor dem 13.09.2026.
    pipeline        INTEGER
);

-- BIB-22 (typisiert) und BIB-23 (Gueltigkeit).
CREATE TABLE kanten (
    nr          INTEGER PRIMARY KEY,
    von         TEXT NOT NULL,
    von_art     TEXT NOT NULL,
    typ         TEXT NOT NULL,
    nach        TEXT NOT NULL,
    nach_art    TEXT NOT NULL,
    gilt_ab     TEXT,
    gilt_bis    TEXT,
    zuversicht  TEXT,
    gesetzt_von TEXT,              -- Auftrag/Herkunft, BIB-17 und BIB-23
    erklaert_in TEXT,              -- die Datei, in deren Frontmatter sie steht
    bib22       INTEGER NOT NULL   -- 1 = Typ steht in BIB-22, 0 = nicht
);
CREATE INDEX kanten_von  ON kanten(von, typ);
CREATE INDEX kanten_nach ON kanten(nach, typ);

CREATE TABLE befunde (
    nr       INTEGER PRIMARY KEY,
    art      TEXT NOT NULL,
    schwere  TEXT NOT NULL,
    betrifft TEXT NOT NULL,
    text     TEXT NOT NULL
);

CREATE TABLE meta (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL
);

-- Volltextsuche (BIB-18b, BIB-18c: Stichwortsuche, BM25, keine Vektoren).
CREATE VIRTUAL TABLE fts_aussagen  USING fts5(beleg_id UNINDEXED, aussage, begruendung, tokenize='unicode61');
CREATE VIRTUAL TABLE fts_zitate    USING fts5(fundstelle_id UNINDEXED, stelle, zitat, tokenize='unicode61');
CREATE VIRTUAL TABLE fts_einheiten USING fts5(einheit_id UNINDEXED, titel, kurzfassung, inhalt, tokenize='unicode61');
"""

# Kantentypen, die der Evidenzgraph (BIB-21) braucht, die BIB-22 aber nicht
# auffuehrt. Sie werden gebaut und gemeldet, nicht auf BIB-22 umgedeutet.
STRUKTURTYPEN = ("hat_fassung", "enthaelt", "entnommen_aus", "siehe_auch")


def oeffne(pfad: str | Path) -> sqlite3.Connection:
    """Oeffnet einen gebauten Index lesend."""
    pfad = Path(pfad)
    if not pfad.is_file():
        raise FileNotFoundError(
            f"Index fehlt: {pfad}. Bauen mit "
            f"'python -m bibliothek.index --ziel {pfad}'."
        )
    db = sqlite3.connect(f"file:{pfad}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


class IndexJeStrang:
    """Eine Index-Verbindung je Strang.

    Der Flask-Entwicklungsserver bedient mehrere Anfragen nebenlaeufig, und
    eine SQLite-Verbindung gehoert genau einem Strang. Weil der Index nur
    gelesen wird (BIB-18b), genuegt eine Verbindung je Strang; Sperren
    braucht es nicht.
    """

    def __init__(self, pfad: str | Path) -> None:
        self.pfad = Path(pfad)
        oeffne(self.pfad).close()  # frueh scheitern, wenn der Index fehlt
        self._lokal = threading.local()

    def verbindung(self) -> sqlite3.Connection:
        db = getattr(self._lokal, "db", None)
        if db is None:
            db = oeffne(self.pfad)
            self._lokal.db = db
        return db

    def execute(self, *args) -> sqlite3.Cursor:
        """Damit sich die Klasse ueberall dort einsetzen laesst, wo ``abfragen``
        eine Verbindung erwartet."""
        return self.verbindung().execute(*args)


def baue_index(wurzel: str | Path, ziel: str | Path) -> Bibliothek:
    """Liest die Bibliothek und schreibt sie komplett neu in ``ziel``."""
    bib = lies_bibliothek(wurzel)
    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    neu = ziel.with_name(ziel.name + ".neu")
    for rest in (neu, Path(str(neu) + "-wal"), Path(str(neu) + "-shm")):
        rest.unlink(missing_ok=True)

    db = sqlite3.connect(neu)
    try:
        db.executescript(SCHEMA)
        _fuelle(db, bib)
        db.commit()
    finally:
        db.close()
    os.replace(neu, ziel)
    return bib


def _fuelle(db: sqlite3.Connection, bib: Bibliothek) -> None:
    frei = lambda h: 1 if h == "freigegeben" else 0  # noqa: E731

    db.executemany(
        "INSERT INTO quellen VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                q.id, q.titel, q.urheber, q.art, q.fundort, q.veroeffentlicht,
                q.abgerufen, q.lizenz, q.qualitaet, q.qualitaet_begruendung,
                q.reichweite, q.reichweite_detail, q.anmerkung, q.herkunft,
                frei(q.herkunft), q.pfad,
            )
            for q in bib.quellen.values()
        ],
    )
    db.executemany(
        "INSERT INTO versionen VALUES (?,?,?,?,?,?)",
        [
            (v.schluessel, v.id, v.quelle_id, v.zeichen, v.herkunft, v.pfad)
            for v in bib.versionen.values()
        ],
    )
    db.executemany(
        "INSERT INTO fundstellen VALUES (?,?,?,?,?,?,?,?,?,?)",
        [
            (
                f.id, f.quelle_id, f.version_id,
                f"{f.quelle_id}/{f.version_id}" if f.version_id else None,
                f.stelle, f.zitat, f.anmerkung, f.herkunft, frei(f.herkunft), f.pfad,
            )
            for f in bib.fundstellen.values()
        ],
    )
    db.executemany(
        "INSERT INTO belege VALUES (?,?,?,?,?,?,?,?,?)",
        [
            (
                b.id, b.fundstelle_id or None, b.gilt_ab, b.zuversicht, b.aussage,
                b.begruendung, b.herkunft, frei(b.herkunft), b.pfad,
            )
            for b in bib.belege.values()
        ],
    )
    db.executemany(
        "INSERT INTO einheiten VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        [
            (
                w.id, w.titel, w.stichwort, w.grad, w.kurzfassung, w.inhalt, w.prueffrage,
                w.gilt_ab, w.herkunft, frei(w.herkunft), w.pfad,
            )
            for w in bib.einheiten.values()
        ],
    )
    for p in bib.pfade.values():
        db.execute(
            "INSERT INTO pfade VALUES (?,?,?,?,?,?,?)",
            (p.id, getattr(p, "reihenfolge", 99), p.titel, p.kurzfassung, p.status,
             p.sprache, p.pfad),
        )
        db.executemany(
            "INSERT INTO abschnitte VALUES (?,?,?,?,?,?)",
            [
                (p.id, a.schluessel, a.nummer, a.titel, a.kern, a.text)
                for a in p.abschnitte
            ],
        )

    for k in getattr(bib, "kapitel", {}).values():
        db.execute(
            "INSERT INTO kapitel VALUES (?,?,?,?,?,?)",
            (k.id, k.pfad_id, k.nummer, k.titel, k.kurzfassung, k.pfad),
        )
        db.executemany(
            "INSERT INTO kapitel_lektionen VALUES (?,?,?)",
            [(k.id, a, r) for r, a in enumerate(k.lektionen)],
        )

    for m in getattr(bib, "mindmaps", {}).values():
        db.execute(
            "INSERT INTO mindmap_analyse VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (m.kapitel, m.kern, m.kernaussage, m.beziehungen, m.layout, m.pfad,
             m.bild, m.bild_breite, m.bild_hoehe, m.bild_titel,
             json.dumps(m.bild_belege, ensure_ascii=False)),
        )
        for rang, achse in enumerate(m.achsen):
            db.execute(
                "INSERT INTO mindmap_achsen VALUES (?,?,?,?,?,?)",
                (m.kapitel, achse.id, rang, achse.frage,
                 achse.eltern, achse.eltern_frage),
            )
            db.executemany(
                "INSERT INTO mindmap_achse_einheiten VALUES (?,?,?,?)",
                [(m.kapitel, achse.id, wid, r)
                 for r, wid in enumerate(achse.einheiten)],
            )

    # BIB-26/27: Die Lektion ist die Darbietungsschicht. Sie nennt ihre
    # Wissenseinheiten in Reihenfolge; die Rueckwaertsfrage ("in welchen
    # Lektionen kommt WE-0004 vor") beantwortet erst dieser Index.
    for l in getattr(bib, "lektionen", {}).values():
        db.execute(
            "INSERT INTO lektionen VALUES (?,?,?,?,?,?,?,?)",
            (l.id, getattr(l, "pfad_id", None), l.kapitel, l.abschnitt, l.nummer,
             l.titel, l.dauer_sek, l.audio),
        )
        db.executemany(
            "INSERT INTO lektion_einheiten VALUES (?,?,?)",
            [(l.id, wid, rang) for rang, wid in enumerate(l.wissenseinheiten)],
        )
        db.executemany(
            "INSERT INTO kapitelmarken VALUES (?,?,?,?)",
            [(l.id, m.sek, m.titel, m.art) for m in l.kapitelmarken],
        )
        db.execute(
            "INSERT INTO lektion_zusatz VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (l.id, l.auftrag, l.zeichen_vertont,
             json.dumps(l.stimmen, ensure_ascii=False), l.erzeugt,
             l.bild, l.bild_breite, l.bild_hoehe, l.bild_titel,
             json.dumps(l.bild_belege, ensure_ascii=False), l.pipeline),
        )

    _kanten(db, bib)

    db.executemany(
        "INSERT INTO fts_aussagen VALUES (?,?,?)",
        [(b.id, b.aussage, b.begruendung) for b in bib.belege.values()],
    )
    db.executemany(
        "INSERT INTO fts_zitate VALUES (?,?,?)",
        [(f.id, f.stelle, f.zitat) for f in bib.fundstellen.values()],
    )
    db.executemany(
        "INSERT INTO fts_einheiten VALUES (?,?,?,?)",
        [(w.id, w.titel, w.kurzfassung, w.inhalt) for w in bib.einheiten.values()],
    )

    db.executemany(
        "INSERT INTO befunde (art, schwere, betrifft, text) VALUES (?,?,?,?)",
        [(f.art, f.schwere, f.betrifft, f.text) for f in bib.befunde],
    )
    db.executemany(
        "INSERT INTO meta VALUES (?,?)",
        [
            ("gebaut_am", dt.datetime.now().astimezone().isoformat(timespec="seconds")),
            ("wurzel", bib.wurzel),
            ("quellen", str(len(bib.quellen))),
            ("versionen", str(len(bib.versionen))),
            ("fundstellen", str(len(bib.fundstellen))),
            ("belege", str(len(bib.belege))),
            ("einheiten", str(len(bib.einheiten))),
            ("pfade", str(len(bib.pfade))),
            ("lektionen", "0"),
            ("befunde", str(len(bib.befunde))),
        ],
    )


def _kanten(db: sqlite3.Connection, bib: Bibliothek) -> None:
    """Baut den Evidenz- und den Begriffsgraphen als typisierte Kanten.

    Der didaktische Graph (BIB-21, Zeile 3) hat im Material keine Knoten —
    Lernziele und Pruefungsfragen als eigene Dinge kommen nach BIB-25 spaeter.
    """
    zeilen: list[tuple] = []

    def kante(von, von_art, typ, nach, nach_art, gilt_ab, zuversicht, gesetzt_von, erklaert_in):
        zeilen.append(
            (
                von, von_art, typ, nach, nach_art, gilt_ab, None, zuversicht,
                gesetzt_von, erklaert_in, 1 if typ in BIB22_TYPEN else 0,
            )
        )

    for v in bib.versionen.values():
        q = bib.quellen.get(v.quelle_id)
        kante(
            v.quelle_id, "quelle", "hat_fassung", v.schluessel, "version",
            q.abgerufen if q else None, None, v.herkunft, v.pfad,
        )
    for f in bib.fundstellen.values():
        if f.version_id and f"{f.quelle_id}/{f.version_id}" in bib.versionen:
            kante(
                f"{f.quelle_id}/{f.version_id}", "version", "enthaelt", f.id, "fundstelle",
                None, None, f.herkunft, f.pfad,
            )
        else:
            # Ohne gesicherte Fassung (BIB-4a, als Befund gemeldet) haengt die
            # Fundstelle direkt an der Quelle. Sonst risse die Kette fuer
            # BIB-20 ab: Aendert sich die Quelle, waere nichts betroffen.
            kante(
                f.quelle_id, "quelle", "enthaelt", f.id, "fundstelle",
                None, None, f.herkunft, f.pfad,
            )
    for b in bib.belege.values():
        if b.fundstelle_id:
            kante(
                b.id, "beleg", "entnommen_aus", b.fundstelle_id, "fundstelle",
                b.gilt_ab, b.zuversicht, b.herkunft, b.pfad,
            )
    for w in bib.einheiten.values():
        for bid in w.belegt_durch:
            beleg = bib.belege.get(bid)
            kante(
                bid, "beleg", "stuetzt", w.id, "einheit",
                beleg.gilt_ab if beleg else None,
                beleg.zuversicht if beleg else None,
                w.herkunft, w.pfad,
            )
        for typ, ziele in (
            ("setzt_voraus", w.setzt_voraus),
            ("widerspricht", w.widerspricht),
            ("siehe_auch", w.siehe_auch),
        ):
            for ziel in ziele:
                kante(w.id, "einheit", typ, ziel, "einheit", w.gilt_ab, None, w.herkunft, w.pfad)

    db.executemany(
        "INSERT INTO kanten (von, von_art, typ, nach, nach_art, gilt_ab, gilt_bis,"
        " zuversicht, gesetzt_von, erklaert_in, bib22) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        zeilen,
    )

    ausserhalb = sorted({z[2] for z in zeilen if z[10] == 0})
    if ausserhalb:
        bib.melde(
            "kantentypen_ausserhalb_bib22",
            "abweichung",
            "kanten",
            "Der Evidenzgraph aus BIB-21 braucht Typen, die BIB-22 nicht auffuehrt: "
            + ", ".join(ausserhalb)
            + ". Sie sind gebaut und in kanten.bib22 = 0 markiert, damit die Luecke "
            "sichtbar bleibt, statt auf einen BIB-22-Typ umgedeutet zu werden.",
        )
    if zeilen and all(z[6] is None for z in zeilen):
        bib.melde(
            "gilt_bis_nirgends",
            "abweichung",
            "kanten",
            f"BIB-23 sieht ein optionales 'gilt_bis' vor. Keine der {len(zeilen)} "
            "Kanten hat eines, weil kein Frontmatter im Material das Feld fuehrt. "
            "Damit ist 'was ist abgelaufen' heute nicht beantwortbar — die Spalte "
            "steht, die Daten fehlen.",
        )
    if zeilen and all(z[7] is None for z in zeilen if z[2] in ("setzt_voraus", "siehe_auch")):
        bib.melde(
            "zuversicht_nur_am_beleg",
            "abweichung",
            "kanten",
            "BIB-23 verlangt eine 'zuversicht' an der Kante. Im Material steht sie "
            "am Beleg. Kanten, die von einem Beleg ausgehen, erben sie; "
            "Einheit-zu-Einheit-Kanten haben keine.",
        )


def _haupt(argv: list[str] | None = None) -> int:
    import pfade
    p = argparse.ArgumentParser(description="Baut index.db aus der Bibliothek.")
    p.add_argument(
        "--wissen",
        default=str(pfade.WISSEN),
        help="Wurzel der Bibliothek (Standard: TEACHBUDDY_WISSEN oder demo/)",
    )
    p.add_argument(
        "--ziel",
        default=str(pfade.INDEX),
        help="wohin der Index geschrieben wird",
    )
    p.add_argument("--still", action="store_true", help="nur Fehler melden")
    a = p.parse_args(argv)

    Path(a.ziel).parent.mkdir(parents=True, exist_ok=True)
    bib = baue_index(a.wissen, a.ziel)
    fehler = [f for f in bib.befunde if f.schwere == "fehler"]
    if not a.still:
        print(f"Index gebaut: {a.ziel}")
        print(
            f"  {len(bib.quellen)} Quellen · {len(bib.versionen)} Versionen · "
            f"{len(bib.fundstellen)} Fundstellen · {len(bib.belege)} Belege · "
            f"{len(bib.einheiten)} Wissenseinheiten · {len(bib.pfade)} Lernpfade"
        )
        print(f"  {len(bib.befunde)} Befunde, davon {len(fehler)} Fehler")
    for f in fehler:
        print(f"  FEHLER {f.art} [{f.betrifft}] {f.text}", file=sys.stderr)
    return 1 if fehler else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(_haupt())
