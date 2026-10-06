"""Kostenerfassung — E-21: sichtbar machen, nicht begrenzen.

Entschieden am 11.09.2026: **keine Obergrenze.** Der Nutzer entscheidet selbst,
wann genug ist — dafür muss er es sehen. Damit ist diese Datei keine Zugabe,
sondern die einzige Kontrolle, die es gibt.

Zwei Kostenarten, beide **gemessen** und nicht hochgerechnet (E-21b):

* **Sprachsitzungen** — Sitzungssekunden mal Minutenpreis. Die Uhr läuft auch
  in Denkpausen (E-20c); genau deshalb schließt sich die Sitzung nach 15 s
  Stille (OBF-13c).
* **Vertonung** — vertonte Zeichen je Folge (POD-7a).

Der Minutenpreis steht in der Konfiguration, nicht hier (E-21c): Preise ändern
sich, und eine falsch angezeigte Zahl ist schlimmer als gar keine.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS sprachsitzung (
    id           TEXT PRIMARY KEY,
    kapitel_id   TEXT NOT NULL,
    begonnen     TEXT NOT NULL,
    beendet      TEXT,
    sekunden     REAL NOT NULL DEFAULT 0,
    preis_minute REAL NOT NULL,
    waehrung     TEXT NOT NULL DEFAULT 'USD'
);
CREATE TABLE IF NOT EXISTS vertonung (
    auftrag_id  TEXT PRIMARY KEY,
    lernpfad_id TEXT,
    lektion_id  TEXT,
    zeichen     INTEGER NOT NULL,
    zeitpunkt   TEXT NOT NULL,
    preis_1k    REAL NOT NULL DEFAULT 0.0
);
-- Live-Recherche im Gespraech (DIS-25). Sie laeuft ueber die bezahlte
-- Schnittstelle, weil niemand im Gespraech Minuten auf einen Abo-CLI-Lauf
-- wartet (TB-5: was der Lernende erlebt, laeuft ueber APIs).
--
-- **Gezaehlt wird der Aufruf, nicht der Preis.** Was eine Websuche kostet,
-- haengt am Modell und aendert sich; eine ausgedachte Zahl waere schlimmer
-- als keine (TB-8). Die Zahl der Aufrufe beantwortet die Frage, die als
-- erste kommt: Wie oft passiert das ueberhaupt? DIS-29 sagt ausdruecklich,
-- erst zu messen, wie oft der Fall eintritt.
CREATE TABLE IF NOT EXISTS recherche (
    nr         INTEGER PRIMARY KEY,
    sitzung_id TEXT,
    kapitel_id TEXT,
    modell     TEXT,
    sekunden   REAL,
    zeitpunkt  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_recherche_zeit ON recherche(zeitpunkt);
CREATE INDEX IF NOT EXISTS ix_sitzung_begonnen ON sprachsitzung(begonnen);
CREATE INDEX IF NOT EXISTS ix_vertonung_pfad   ON vertonung(lernpfad_id);
"""


def _jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).astimezone().isoformat(timespec="seconds")


class Kosten:
    def __init__(self, pfad: str | Path) -> None:
        self.pfad = Path(pfad)
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self) -> sqlite3.Connection:
        # **WAL wie beim Lernstand.** Die beiden Datenbanken sind Geschwister
        # und liefen verschieden: `lernstand.db` im WAL-Modus, diese hier im
        # Journalmodus, in dem ein Leser den Schreiber sperrt.
        #
        # Am 14.09.2026 hat ein gleichzeitig lesendes Skript
        # `sitzung_endet` mit "database is locked" auf einen 500er laufen
        # lassen. Die Folge waere still: Der Browser fängt den Fehler ab und
        # gilt die Sitzung als zu — im Kostenbuch bleibt sie **offen stehen**.
        # Und das Kostenbuch ist nach E-21 die einzige Kontrolle, weil es
        # keine Obergrenze gibt. Eine Sitzung, die dort fehlt, ist schlimmer
        # als eine, die zu teuer war.
        db = sqlite3.connect(self.pfad, timeout=5.0)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        return db

    # -- Sprachsitzungen ---------------------------------------------------

    def sitzung_beginnt(self, sitzung_id: str, kapitel_id: str,
                        preis_minute: float, waehrung: str = "USD") -> None:
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO sprachsitzung"
                " (id, kapitel_id, begonnen, preis_minute, waehrung)"
                " VALUES (?,?,?,?,?)",
                (sitzung_id, kapitel_id, _jetzt(), preis_minute, waehrung))

    def sitzung_endet(self, sitzung_id: str, sekunden: float) -> None:
        """Die tatsächlich offene Zeit, vom Client gemeldet.

        Nicht die Sprechzeit: Bei einer Sprachsitzung zählt die geöffnete
        Verbindung, auch die Stille darin (E-20c).
        """
        with self._db() as db:
            db.execute("UPDATE sprachsitzung SET beendet=?, sekunden=? WHERE id=?",
                       (_jetzt(), float(sekunden), sitzung_id))

    # -- Vertonung ---------------------------------------------------------

    def recherche(self, *, sitzung_id: str | None, kapitel_id: str | None,
                  modell: str, sekunden: float) -> None:
        """Einen Recherche-Aufruf verzeichnen (DIS-25, E-21)."""
        db = self._db()
        db.execute(
            "INSERT INTO recherche (sitzung_id, kapitel_id, modell, sekunden, zeitpunkt)"
            " VALUES (?,?,?,?,?)",
            (sitzung_id, kapitel_id, modell, sekunden, _jetzt()))
        db.commit()

    def vertonung(self, auftrag_id: str, zeichen: int, *,
                  lernpfad_id: str | None = None, lektion_id: str | None = None,
                  preis_1k: float = 0.0) -> None:
        with self._db() as db:
            db.execute(
                "INSERT OR REPLACE INTO vertonung"
                " (auftrag_id, lernpfad_id, lektion_id, zeichen, zeitpunkt, preis_1k)"
                " VALUES (?,?,?,?,?,?)",
                (auftrag_id, lernpfad_id, lektion_id, int(zeichen), _jetzt(), preis_1k))

    # -- Auskunft ----------------------------------------------------------

    def _summe(self, seit: str) -> dict[str, Any]:
        with self._db() as db:
            z = db.execute(
                "SELECT COUNT(*) n, COALESCE(SUM(sekunden),0) s,"
                "       COALESCE(SUM(sekunden/60.0*preis_minute),0) betrag"
                " FROM sprachsitzung WHERE begonnen >= ?", (seit,)).fetchone()
            v = db.execute(
                "SELECT COALESCE(SUM(zeichen),0) zeichen,"
                "       COALESCE(SUM(zeichen/1000.0*preis_1k),0) betrag"
                " FROM vertonung WHERE zeitpunkt >= ?", (seit,)).fetchone()
            # Ohne Betrag: Was eine Websuche kostet, wissen wir nicht genau
            # genug, um es hinzuschreiben. Die Zahl der Aufrufe beantwortet
            # die Frage, die zuerst kommt (DIS-29).
            r = db.execute(
                "SELECT COUNT(*) n FROM recherche WHERE zeitpunkt >= ?",
                (seit,)).fetchone()
        return {
            "recherchen": r["n"],
            "gespraeche": z["n"],
            "sitzungsminuten": round(z["s"] / 60.0, 1),
            "gespraechs_betrag": round(z["betrag"], 2),
            "vertonung_zeichen": v["zeichen"],
            "vertonung_betrag": round(v["betrag"], 2),
            "betrag": round(z["betrag"] + v["betrag"], 2),
        }

    def uebersicht(self, waehrung: str = "USD") -> dict[str, Any]:
        heute = dt.date.today().isoformat()
        monat = dt.date.today().replace(day=1).isoformat()
        with self._db() as db:
            pfade = db.execute(
                "SELECT lernpfad_id, COALESCE(SUM(zeichen),0) zeichen,"
                "       COALESCE(SUM(zeichen/1000.0*preis_1k),0) betrag"
                " FROM vertonung WHERE lernpfad_id IS NOT NULL"
                " GROUP BY lernpfad_id").fetchall()
        return {
            "heute": self._summe(heute),
            "monat": self._summe(monat),
            # E-21d: die Zahl, die beantwortet, ob sich ein weiterer Lernpfad lohnt.
            "je_lernpfad": [
                {"lernpfad_id": r["lernpfad_id"],
                 "vertonung_zeichen": r["zeichen"],
                 "vertonung_betrag": round(r["betrag"], 2)}
                for r in pfade
            ],
            "waehrung": waehrung,
            "_hinweis": "E-21: keine Obergrenze. Alle Zahlen gemessen, nicht hochgerechnet.",
        }
