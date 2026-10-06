"""Der Lernstand — eigene Wahrheit, eigene Datei (OBF-7).

Der Lernstand ist **keine Ableitung aus Dateien**. Er entsteht beim Hoeren
und Antworten und laesst sich aus der Bibliothek nicht rekonstruieren.
Deshalb liegt er nicht im Index (der ist Wegwerfware, BIB-18b), sondern in
einer eigenen SQLite-Datei, die den Neubau des Index ueberlebt.

Er liegt auf dem Server und nicht nur im Browser (OBF-7): Sonst ist er weg,
sobald der Browser aufraeumt, und auf dem Laptop weiss die App nicht, was auf
dem Telefon gehoert wurde.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from pathlib import Path
from typing import Any, Iterable

__all__ = ["FRAGEN_ZUSTAENDE", "Lernstand", "jetzt"]

FRAGEN_ZUSTAENDE = ("offen", "teilweise", "fertig")

SCHEMA = """
CREATE TABLE IF NOT EXISTS fortschritt (
    lektion_id   TEXT PRIMARY KEY,
    position_sek REAL NOT NULL,
    fragen       TEXT NOT NULL,
    zeitpunkt    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS einstellungen (
    schluessel TEXT PRIMARY KEY,
    wert       TEXT NOT NULL,
    zeitpunkt  TEXT NOT NULL
);

-- Antworten werden gespeichert, auch wenn sie heute niemand bewerten kann
-- (PRF-7 braucht ein Modell). Wegwerfen waere der teurere Fehler: Der
-- Lernende hat sie einmal geschrieben.
CREATE TABLE IF NOT EXISTS antworten (
    nr          INTEGER PRIMARY KEY,
    frage_id    TEXT NOT NULL,
    text        TEXT NOT NULL,
    zeitpunkt   TEXT NOT NULL,
    bewertung   TEXT,
    begruendung TEXT
);
CREATE INDEX IF NOT EXISTS antworten_frage ON antworten(frage_id);

-- Rueckmeldungen des Menschen zu einer einzelnen Wissenseinheit (OBF-19).
--
-- Rückmeldung vom 13.09.2026: „gib mir bei jeder Einheit ein kleines Symbol, wo ich
-- Feedback ablassen kann." Bis dahin lief jede Rueckmeldung ueber den Chat
-- mit mir und war zwei Tage spaeter nicht mehr auffindbar — POD-16 und E-25
-- sind beide aus muendlichem Feedback entstanden, und ein Teil davon
-- (Beispiele und Anekdoten) ist dabei verlorengegangen.
--
-- Sie gehoert hierher und nicht in den Index: Die Bibliothek wird aus
-- Dateien gebaut und ist wegwerfbar (BIB-18b), eine Rueckmeldung nicht.
--
-- `pipeline` und `erzeugt` werden **mitgeschrieben, nicht nachgeschlagen**.
-- Eine Rueckmeldung gilt fuer den Stand, den der Mensch gehoert hat. Wer sie
-- spaeter gegen die dann aktuelle Fassung liest, deutet sie falsch.
CREATE TABLE IF NOT EXISTS rueckmeldungen (
    nr          INTEGER PRIMARY KEY,
    lektion_id  TEXT NOT NULL,
    einheit_id  TEXT,
    art         TEXT NOT NULL,
    text        TEXT,
    pipeline    INTEGER,
    erzeugt     TEXT,
    zeitpunkt   TEXT NOT NULL,
    erledigt    TEXT
);
CREATE INDEX IF NOT EXISTS rueckmeldungen_lektion
    ON rueckmeldungen(lektion_id);

-- Der Rueckkanal aus dem Gespraech (DIS-9, OBF-18).
--
-- Was live recherchiert wurde, ist **ungeprueft** (DIS-28) und gehoert
-- deshalb nicht in die Bibliothek. Es landet hier: auffindbar, mit seiner
-- Frage und seiner Sitzung, und als das gekennzeichnet, was es ist.
--
-- `auftrag = 1` heisst: Der Partner hat die Luecke als Rechercheauftrag
-- festgehalten, statt sie zu beantworten. Dann steht in `antwort` nichts.
CREATE TABLE IF NOT EXISTS recherchen (
    nr           INTEGER PRIMARY KEY,
    sitzung_id   TEXT,
    kapitel_id   TEXT,
    frage        TEXT NOT NULL,
    zusammenhang TEXT,
    antwort      TEXT,
    auftrag      INTEGER NOT NULL DEFAULT 0,
    zeitpunkt    TEXT NOT NULL,
    erledigt     TEXT
);
CREATE INDEX IF NOT EXISTS recherchen_kapitel ON recherchen(kapitel_id);

-- Der Agenda-Zustand einer Sitzung (DIS-16). Er gehoert dem Lernenden, nicht
-- der Bibliothek: Ob ein Punkt sitzt, steht in keiner Quelle.
CREATE TABLE IF NOT EXISTS agenda_stand (
    sitzung_id  TEXT NOT NULL,
    punkt_id    TEXT NOT NULL,
    urteil      TEXT NOT NULL,
    begruendung TEXT,
    zeitpunkt   TEXT NOT NULL,
    PRIMARY KEY (sitzung_id, punkt_id)
);

-- Der Gespraechsverlauf. Er gehoert hierher und nicht in den Index: Was
-- gesprochen wurde, laesst sich aus der Bibliothek nicht rekonstruieren.
--
-- Der Ton laeuft direkt vom Browser zum Anbieter (E-20a), der Server hoert also
-- nicht mit. Was hier ankommt, schickt der Browser aus den Mitschriften der
-- Sitzung. Bleibt es aus, ist der Verlauf leer, und das wird gesagt statt
-- gefuellt.
CREATE TABLE IF NOT EXISTS gespraech (
    nr         INTEGER PRIMARY KEY,
    sitzung_id TEXT NOT NULL,
    kapitel_id TEXT NOT NULL,
    rolle      TEXT NOT NULL,          -- lernender | partner
    text       TEXT NOT NULL,
    zeitpunkt  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS gespraech_sitzung ON gespraech(sitzung_id);
CREATE INDEX IF NOT EXISTS gespraech_kapitel ON gespraech(kapitel_id, nr);
"""


def jetzt() -> str:
    """Zeitstempel mit Zone — ein Stempel ohne Zone ist ein Fehler mit Ansage,
    sobald Server und Datenbanken in verschiedenen Zonen laufen."""
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class Lernstand:
    """Zugriff auf ``lernstand.db``. Eine Verbindung je Aufruf, kurz gehalten."""

    def __init__(self, pfad: str | Path) -> None:
        self.pfad = Path(pfad)
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with self._db() as db:
            db.executescript(SCHEMA)

    def _db(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.pfad, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    # -- Fortschritt -------------------------------------------------------

    def fortschritt(self, lektion_id: str) -> dict[str, Any] | None:
        with self._db() as db:
            r = db.execute(
                "SELECT * FROM fortschritt WHERE lektion_id = ?", (lektion_id,)
            ).fetchone()
        return dict(r) if r else None

    def alle(self) -> dict[str, dict[str, Any]]:
        with self._db() as db:
            return {
                r["lektion_id"]: dict(r) for r in db.execute("SELECT * FROM fortschritt")
            }

    def setze(
        self,
        lektion_id: str,
        position_sek: float,
        fragen: str,
        zeitpunkt: str | None = None,
    ) -> dict[str, Any]:
        """Schreibt den Fortschritt. Ein aelterer Stand ueberschreibt keinen
        neueren — der Server entscheidet, nicht der Browser (R-3)."""
        if fragen not in FRAGEN_ZUSTAENDE:
            raise ValueError(f"fragen muss eines von {FRAGEN_ZUSTAENDE} sein, nicht {fragen!r}")
        if position_sek < 0:
            raise ValueError("position_sek darf nicht negativ sein")
        stempel = zeitpunkt or jetzt()
        with self._db() as db:
            alt = db.execute(
                "SELECT zeitpunkt FROM fortschritt WHERE lektion_id = ?", (lektion_id,)
            ).fetchone()
            if alt is not None and _spaeter(alt["zeitpunkt"], stempel):
                return {
                    "uebernommen": False,
                    "grund": "es liegt ein spaeterer Stand vor",
                    "vorhanden_seit": alt["zeitpunkt"],
                }
            db.execute(
                "INSERT INTO fortschritt (lektion_id, position_sek, fragen, zeitpunkt)"
                " VALUES (?,?,?,?)"
                " ON CONFLICT(lektion_id) DO UPDATE SET"
                "   position_sek = excluded.position_sek,"
                "   fragen       = excluded.fragen,"
                "   zeitpunkt    = excluded.zeitpunkt",
                (lektion_id, float(position_sek), fragen, stempel),
            )
        return {"uebernommen": True, "zeitpunkt": stempel}

    def nachtrag(self, saetze: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """APP-7: offline gesammelte Staende einspielen.

        Bei Konflikt gewinnt der spaetere Zeitpunkt. Kommen mehrere Saetze zur
        selben Lektion, entscheidet derselbe Vergleich — die Reihenfolge in
        der Liste ist ohne Bedeutung.
        """
        uebernommen = 0
        verworfen: list[dict[str, Any]] = []
        for satz in saetze:
            lektion_id = satz.get("lektion_id")
            zeitpunkt = satz.get("zeitpunkt")
            if not lektion_id or not zeitpunkt:
                verworfen.append(
                    {"satz": satz, "grund": "lektion_id und zeitpunkt sind Pflicht"}
                )
                continue
            try:
                ergebnis = self.setze(
                    lektion_id,
                    float(satz.get("position_sek", 0)),
                    str(satz.get("fragen", "offen")),
                    zeitpunkt=str(zeitpunkt),
                )
            except (ValueError, TypeError) as fehler:
                verworfen.append({"satz": satz, "grund": str(fehler)})
                continue
            if ergebnis["uebernommen"]:
                uebernommen += 1
            else:
                verworfen.append(
                    {
                        "lektion_id": lektion_id,
                        "zeitpunkt": zeitpunkt,
                        "grund": ergebnis["grund"],
                        "vorhanden_seit": ergebnis.get("vorhanden_seit"),
                    }
                )
        return {"uebernommen": uebernommen, "verworfen": verworfen}

    # -- Einstellungen -----------------------------------------------------

    def einstellungen(self) -> dict[str, Any]:
        with self._db() as db:
            roh = {r["schluessel"]: r["wert"] for r in db.execute("SELECT * FROM einstellungen")}
        return {"tempo": float(roh.get("tempo", 1.0))}

    def setze_einstellung(self, schluessel: str, wert: str) -> None:
        with self._db() as db:
            db.execute(
                "INSERT INTO einstellungen (schluessel, wert, zeitpunkt) VALUES (?,?,?)"
                " ON CONFLICT(schluessel) DO UPDATE SET"
                "   wert = excluded.wert, zeitpunkt = excluded.zeitpunkt",
                (schluessel, wert, jetzt()),
            )

    # -- Antworten ---------------------------------------------------------

    def merke_antwort(
        self, frage_id: str, text: str, bewertung: str | None, begruendung: str | None
    ) -> int:
        with self._db() as db:
            cur = db.execute(
                "INSERT INTO antworten (frage_id, text, zeitpunkt, bewertung, begruendung)"
                " VALUES (?,?,?,?,?)",
                (frage_id, text, jetzt(), bewertung, begruendung),
            )
        return int(cur.lastrowid)

    # -- Rueckmeldungen (OBF-19) -------------------------------------------

    def merke_rueckmeldung(
        self,
        lektion_id: str,
        *,
        einheit_id: str | None,
        art: str,
        text: str | None,
        pipeline: int | None,
        erzeugt: str | None,
    ) -> dict[str, Any]:
        db = self._db()
        wann = jetzt()
        cur = db.execute(
            "INSERT INTO rueckmeldungen"
            " (lektion_id, einheit_id, art, text, pipeline, erzeugt, zeitpunkt)"
            " VALUES (?,?,?,?,?,?,?)",
            (lektion_id, einheit_id, art, text, pipeline, erzeugt, wann),
        )
        db.commit()
        return {"nr": cur.lastrowid, "zeitpunkt": wann}

    def rueckmeldungen(
        self, lektion_id: str | None = None, *, offen: bool = False
    ) -> list[dict[str, Any]]:
        wo, werte = [], []
        if lektion_id:
            wo.append("lektion_id = ?")
            werte.append(lektion_id)
        if offen:
            wo.append("erledigt IS NULL")
        satz = (" WHERE " + " AND ".join(wo)) if wo else ""
        return [
            dict(r)
            for r in self._db().execute(
                "SELECT * FROM rueckmeldungen" + satz + " ORDER BY nr DESC",
                werte,
            )
        ]

    # -- Rueckkanal aus dem Gespraech (DIS-9, DIS-16, OBF-18) --------------

    def merke_recherche(
        self,
        frage: str,
        *,
        sitzung_id: str | None = None,
        kapitel_id: str | None = None,
        zusammenhang: str | None = None,
        antwort: str | None = None,
        auftrag: bool = False,
    ) -> dict[str, Any]:
        db = self._db()
        wann = jetzt()
        cur = db.execute(
            "INSERT INTO recherchen"
            " (sitzung_id, kapitel_id, frage, zusammenhang, antwort, auftrag, zeitpunkt)"
            " VALUES (?,?,?,?,?,?,?)",
            (sitzung_id, kapitel_id, frage, zusammenhang, antwort,
             1 if auftrag else 0, wann),
        )
        db.commit()
        return {"nr": cur.lastrowid, "zeitpunkt": wann}

    def recherchen(
        self, kapitel_id: str | None = None, *, nur_auftraege: bool = False
    ) -> list[dict[str, Any]]:
        wo, werte = [], []
        if kapitel_id:
            wo.append("kapitel_id = ?")
            werte.append(kapitel_id)
        if nur_auftraege:
            wo.append("auftrag = 1")
        satz = (" WHERE " + " AND ".join(wo)) if wo else ""
        return [
            dict(r)
            for r in self._db().execute(
                "SELECT * FROM recherchen" + satz + " ORDER BY nr DESC", werte)
        ]

    def merke_agenda(self, sitzung_id: str, punkt_id: str, urteil: str,
                     begruendung: str | None = None) -> dict[str, Any]:
        db = self._db()
        wann = jetzt()
        db.execute(
            "INSERT INTO agenda_stand"
            " (sitzung_id, punkt_id, urteil, begruendung, zeitpunkt)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(sitzung_id, punkt_id) DO UPDATE SET"
            "   urteil = excluded.urteil,"
            "   begruendung = excluded.begruendung,"
            "   zeitpunkt = excluded.zeitpunkt",
            (sitzung_id, punkt_id, urteil, begruendung, wann),
        )
        db.commit()
        return {"punkt": punkt_id, "urteil": urteil, "zeitpunkt": wann}

    def agenda_stand(self, sitzung_id: str) -> list[dict[str, Any]]:
        return [
            dict(r)
            for r in self._db().execute(
                "SELECT * FROM agenda_stand WHERE sitzung_id = ? ORDER BY zeitpunkt",
                (sitzung_id,))
        ]

    def antworten(self, frage_id: str) -> list[dict[str, Any]]:
        with self._db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM antworten WHERE frage_id = ? ORDER BY nr", (frage_id,)
                )
            ]

    # -- Gespraech ---------------------------------------------------------

    ROLLEN = ("lernender", "partner")

    def merke_beitraege(
        self, sitzung_id: str, kapitel_id: str, beitraege: Iterable[dict[str, Any]]
    ) -> int:
        """Mitschrift einer Sprachsitzung ablegen.

        Doppelte gehen hier durch: Der Browser schickt in Schueben, und ein
        verlorener Schub ist schlimmer als eine doppelte Zeile. Aufgeraeumt
        wird beim Lesen.
        """
        saetze = []
        for b in beitraege:
            text = str(b.get("text") or "").strip()
            rolle = str(b.get("rolle") or "").strip()
            if not text or rolle not in self.ROLLEN:
                continue
            saetze.append((sitzung_id, kapitel_id, rolle, text, jetzt()))
        if not saetze:
            return 0
        with self._db() as db:
            db.executemany(
                "INSERT INTO gespraech (sitzung_id, kapitel_id, rolle, text, zeitpunkt)"
                " VALUES (?,?,?,?,?)",
                saetze,
            )
        return len(saetze)

    def verlauf(self, sitzung_id: str) -> list[dict[str, Any]]:
        with self._db() as db:
            return [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM gespraech WHERE sitzung_id = ? ORDER BY nr",
                    (sitzung_id,),
                )
            ]

    def sitzungen_zum_kapitel(self, kapitel_id: str, grenze: int = 3) -> list[dict[str, Any]]:
        """Die letzten Sitzungen zu einem Kapitel, juengste zuletzt.

        Daraus baut der naechste Sitzungsprompt sein Gedaechtnis. ``grenze``
        deckelt das: Ein Prompt, der jedes je gesprochene Wort mitschleppt,
        wird mit jeder Sitzung teurer und am Ende unbrauchbar.
        """
        with self._db() as db:
            ids = [
                r["sitzung_id"]
                for r in db.execute(
                    "SELECT sitzung_id, MAX(nr) AS letzte FROM gespraech"
                    " WHERE kapitel_id = ? GROUP BY sitzung_id"
                    " ORDER BY letzte DESC LIMIT ?",
                    (kapitel_id, int(grenze)),
                )
            ]
            ids.reverse()
            return [
                {"sitzung_id": sid, "beitraege": [
                    dict(r) for r in db.execute(
                        "SELECT rolle, text, zeitpunkt FROM gespraech"
                        " WHERE sitzung_id = ? ORDER BY nr", (sid,))
                ]}
                for sid in ids
            ]


def _spaeter(a: str, b: str) -> bool:
    """Ist ``a`` spaeter als ``b``? Vergleicht als Zeitpunkt, nicht als Text —
    zwei ISO-Stempel mit verschiedener Zone sortieren als Text falsch."""
    pa, pb = _zeit(a), _zeit(b)
    if pa is None or pb is None:
        return a > b
    return pa > pb


def _zeit(text: str) -> dt.datetime | None:
    try:
        wert = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if wert.tzinfo is None:
        wert = wert.astimezone()
    return wert
