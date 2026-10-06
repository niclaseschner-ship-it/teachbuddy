"""Fragen an den Index (BIB-18b).

Das ist der Teil, den Dateien schlecht koennen: Rueckwaertskanten,
Volltextsuche, Belegaufloesung und die Frage aus BIB-20 — *welche Artefakte
veralten, wenn sich hier etwas aendert*.

Alles hier ist lesend. Geschrieben wird nur in der Bibliothek (``TEACHBUDDY_WISSEN``) von
Hand und in den Lernstand (``dienst/lernstand.py``).
"""

from __future__ import annotations

import sqlite3
from typing import Any, Iterable, Sequence

__all__ = [
    "befunde",
    "beleg",
    "belege_ausgeschrieben",
    "begriffsbaum",
    "einheit",
    "kette_abwaerts",
    "lernpfad",
    "meta",
    "rueckwaerts",
    "suche",
    "veraltet_durch",
    "vorwaerts",
]

# Der Evidenzgraph flieszt nicht in Kantenrichtung: 'entnommen_aus' zeigt vom
# Beleg auf die Fundstelle, die Wirkung laeuft umgekehrt. Deshalb je Typ die
# Richtung, in der sich eine Aenderung fortpflanzt (BIB-20).
_WEITERGABE: tuple[tuple[str, str], ...] = (
    ("hat_fassung", "vor"),
    ("enthaelt", "vor"),
    ("entnommen_aus", "rueck"),
    ("stuetzt", "vor"),
)


# --------------------------------------------------------------------------
# Grundauskuenfte
# --------------------------------------------------------------------------


def meta(db: sqlite3.Connection) -> dict[str, str]:
    return {r["schluessel"]: r["wert"] for r in db.execute("SELECT * FROM meta")}


def befunde(db: sqlite3.Connection, schwere: str | None = None) -> list[dict[str, Any]]:
    if schwere:
        rows = db.execute("SELECT * FROM befunde WHERE schwere = ? ORDER BY nr", (schwere,))
    else:
        rows = db.execute("SELECT * FROM befunde ORDER BY nr")
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Kanten
# --------------------------------------------------------------------------


def _kanten(
    db: sqlite3.Connection,
    spalte: str,
    knoten: str,
    typ: str | Sequence[str] | None,
    stichtag: str | None,
) -> list[dict[str, Any]]:
    bedingung = [f"{spalte} = ?"]
    werte: list[Any] = [knoten]
    if typ:
        typen = [typ] if isinstance(typ, str) else list(typ)
        bedingung.append("typ IN (" + ",".join("?" * len(typen)) + ")")
        werte += typen
    if stichtag:
        bedingung.append("(gilt_ab IS NULL OR gilt_ab <= ?)")
        werte.append(stichtag)
        bedingung.append("(gilt_bis IS NULL OR gilt_bis >= ?)")
        werte.append(stichtag)
    sql = "SELECT * FROM kanten WHERE " + " AND ".join(bedingung) + " ORDER BY typ, nr"
    return [dict(r) for r in db.execute(sql, werte)]


def vorwaerts(
    db: sqlite3.Connection,
    knoten: str,
    typ: str | Sequence[str] | None = None,
    stichtag: str | None = None,
) -> list[dict[str, Any]]:
    """Kanten, die von ``knoten`` ausgehen."""
    return _kanten(db, "von", knoten, typ, stichtag)


def rueckwaerts(
    db: sqlite3.Connection,
    knoten: str,
    typ: str | Sequence[str] | None = None,
    stichtag: str | None = None,
) -> list[dict[str, Any]]:
    """Kanten, die auf ``knoten`` zeigen.

    Das ist die Frage, fuer die es den Index ueberhaupt gibt: In den Dateien
    steht nur die Hinrichtung (BIB-24), und *wer zeigt auf mich* waere sonst
    ein Scan ueber das ganze Repo.
    """
    return _kanten(db, "nach", knoten, typ, stichtag)


# --------------------------------------------------------------------------
# Volltextsuche (BIB-18c: Stichwort, BM25, keine Vektoren)
# --------------------------------------------------------------------------

_FELDER = {
    "aussagen": ("fts_aussagen", "beleg_id", ("aussage", "begruendung")),
    "zitate": ("fts_zitate", "fundstelle_id", ("stelle", "zitat")),
    "einheiten": ("fts_einheiten", "einheit_id", ("titel", "kurzfassung", "inhalt")),
}


def suche(
    db: sqlite3.Connection,
    text: str,
    *,
    arten: Iterable[str] | None = None,
    grenze: int = 20,
) -> list[dict[str, Any]]:
    """Sucht in Aussagen, Zitaten und Einheiteninhalten.

    ``text`` wird als FTS5-Ausdruck versucht; ist er als solcher ungueltig
    (Anfuehrungszeichen, ``*``, ``:`` in einer Nutzereingabe), wird er als
    Phrase gesucht statt einen Fehler zu werfen.
    """
    arten = list(arten) if arten else list(_FELDER)
    treffer: list[dict[str, Any]] = []
    for art in arten:
        tabelle, schluessel, spalten = _FELDER[art]
        sql = (
            f"SELECT {schluessel} AS id, bm25({tabelle}) AS rang, "
            + ", ".join(f"snippet({tabelle}, {i + 1}, '[', ']', '…', 12) AS f{i}"
                        for i in range(len(spalten)))
            + f" FROM {tabelle} WHERE {tabelle} MATCH ? ORDER BY rang LIMIT ?"
        )
        for ausdruck in (text, _als_phrase(text)):
            try:
                rows = db.execute(sql, (ausdruck, grenze)).fetchall()
                break
            except sqlite3.OperationalError:
                rows = []
        for r in rows:
            treffer.append(
                {
                    "art": art,
                    "id": r["id"],
                    "rang": r["rang"],
                    "stellen": {s: r[f"f{i}"] for i, s in enumerate(spalten)},
                }
            )
    treffer.sort(key=lambda t: t["rang"])
    return treffer[:grenze]


def _als_phrase(text: str) -> str:
    return '"' + text.replace('"', " ") + '"'


# --------------------------------------------------------------------------
# Belege aufloesen
# --------------------------------------------------------------------------


def beleg(db: sqlite3.Connection, beleg_id: str) -> dict[str, Any] | None:
    """Ein Beleg in der Form aus dem Datenvertrag (``_beleg_detail_beispiel``).

    Der Wortlaut steht nicht am Beleg, sondern an der Fundstelle (BIB-8).
    Hier wird die Kette Beleg → Fundstelle → Quellenversion → Quelle
    zusammengesetzt.
    """
    r = db.execute(
        """
        SELECT b.id, b.aussage, b.begruendung, b.zuversicht, b.gilt_ab,
               b.herkunft, b.freigegeben, b.pfad,
               f.id AS f_id, f.stelle, f.zitat, f.anmerkung AS f_anmerkung,
               f.version_id,
               q.id AS q_id, q.titel AS q_titel, q.urheber, q.art AS q_art,
               q.fundort, q.veroeffentlicht, q.abgerufen, q.qualitaet,
               q.reichweite
          FROM belege b
          LEFT JOIN fundstellen f ON f.id = b.fundstelle_id
          LEFT JOIN quellen     q ON q.id = f.quelle_id
         WHERE b.id = ?
        """,
        (beleg_id,),
    ).fetchone()
    if r is None:
        return None
    return {
        "id": r["id"],
        "aussage": r["aussage"],
        "zitat": r["zitat"],
        "stelle": r["stelle"],
        "begruendung": r["begruendung"],
        "fundstelle_id": r["f_id"],
        "fundstelle_anmerkung": r["f_anmerkung"] or None,
        "quelle": None
        if r["q_id"] is None
        else {
            "id": r["q_id"],
            "titel": r["q_titel"],
            "urheber": r["urheber"],
            "art": r["q_art"],
            "fundort": r["fundort"],
            "veroeffentlicht": r["veroeffentlicht"],
            "abgerufen": r["abgerufen"],
            "qualitaet": r["qualitaet"],
            "reichweite": r["reichweite"],
            "version": r["version_id"],
        },
        "zuversicht": r["zuversicht"],
        "gilt_ab": r["gilt_ab"],
        "freigegeben": bool(r["freigegeben"]),
        "herkunft": r["herkunft"],
    }


def belege_ausgeschrieben(db: sqlite3.Connection, ids: Sequence[str]) -> dict[str, Any]:
    """Die Kurzform fuer R-5: Belege reisen **mit**, nicht als nachzuladende IDs.

    Im Zug ist der Server nicht erreichbar. Ein Beleg, der dann fehlt, ist genau
    der Zustand, den TB-1 ausschlieszt — deshalb kommt er ausgeschrieben in
    jeder Antwort mit, in der auf ihn verwiesen wird.

    Unbekannte IDs werden **nicht** verschwiegen: Sie stehen mit
    ``{"fehlt": true}`` drin, damit die Oberflaeche „Beleg fehlt" zeigen kann
    statt „belegt" zu behaupten.
    """
    ausgabe: dict[str, Any] = {}
    for bid in dict.fromkeys(ids):
        voll = beleg(db, bid)
        if voll is None:
            ausgabe[bid] = {"fehlt": True, "grund": "nicht in der Bibliothek"}
            continue
        ausgabe[bid] = {
            "aussage": voll["aussage"],
            "zitat": voll["zitat"],
            "stelle": voll["stelle"],
            "quelle_id": (voll["quelle"] or {}).get("id"),
            "zuversicht": voll["zuversicht"],
            "freigegeben": voll["freigegeben"],
        }
    return ausgabe


# --------------------------------------------------------------------------
# Wissenseinheiten und Lernpfade
# --------------------------------------------------------------------------


def einheit(db: sqlite3.Connection, we_id: str) -> dict[str, Any] | None:
    r = db.execute("SELECT * FROM einheiten WHERE id = ?", (we_id,)).fetchone()
    if r is None:
        return None
    daten = dict(r)
    daten["freigegeben"] = bool(daten["freigegeben"])
    daten["belege"] = [
        k["von"] for k in rueckwaerts(db, we_id, "stuetzt")
    ]
    daten["setzt_voraus"] = [k["nach"] for k in vorwaerts(db, we_id, "setzt_voraus")]
    daten["baut_auf_mir_auf"] = [k["von"] for k in rueckwaerts(db, we_id, "setzt_voraus")]
    daten["widerspricht"] = [k["nach"] for k in vorwaerts(db, we_id, "widerspricht")]
    daten["siehe_auch"] = [k["nach"] for k in vorwaerts(db, we_id, "siehe_auch")]
    return daten


def lernpfad(db: sqlite3.Connection, pfad_id: str) -> dict[str, Any] | None:
    r = db.execute("SELECT * FROM pfade WHERE id = ?", (pfad_id,)).fetchone()
    if r is None:
        return None
    daten = dict(r)
    daten["abschnitte"] = [
        dict(a)
        for a in db.execute(
            "SELECT * FROM abschnitte WHERE pfad_id = ? ORDER BY nummer", (pfad_id,)
        )
    ]
    return daten


def begriffsbaum(
    db: sqlite3.Connection,
    we_ids: Sequence[str],
    achsen: "Sequence[dict[str, Any]] | None" = None,
) -> list[dict[str, Any]]:
    """Baut aus ``setzt_voraus`` den Knotenbaum fuer die Mindmap (MMP-1).

    Die Ordnung wird **abgelesen**, nicht erfunden: Wurzeln sind die
    Einheiten der Menge, die innerhalb der Menge nichts voraussetzen; Kind
    ist, wer den Elternknoten voraussetzt. Wer mehrere Voraussetzungen hat,
    haengt unter der ersten und wird bei den uebrigen als ``auch_unter``
    vermerkt, statt doppelt gezeichnet zu werden.

    ``achsen`` ist die Strukturanalyse des Kapitels (E-19a). Liegt sie vor,
    haengen die Einheiten unter ihrer Achse statt frei nebeneinander. Ohne sie
    bleibt es beim reinen Voraussetzungsbaum — geraten wird keine Gliederung.

    **Die Beschriftung ist das Stichwort, nicht der Titel** (MMP-3). Der
    ``titel`` einer Wissenseinheit ist eine Behauptung, also ein ganzer Satz;
    er wandert nach ``satz`` und erscheint erst beim Aufklappen.
    """
    menge = [w for w in dict.fromkeys(we_ids) if w]
    vorhanden = {
        r["id"]: dict(r)
        for r in db.execute(
            "SELECT * FROM einheiten WHERE id IN (%s)" % ",".join("?" * len(menge)),
            menge,
        )
    } if menge else {}

    voraus: dict[str, list[str]] = {}
    for wid in vorhanden:
        voraus[wid] = [
            k["nach"] for k in vorwaerts(db, wid, "setzt_voraus") if k["nach"] in vorhanden
        ]

    # Ohne Analyse ist die ganze Menge eine einzige, namenlose Gruppe.
    gruppen: list[dict[str, Any]] = [
        {"id": a.get("id"), "frage": a.get("frage"),
         "eltern": a.get("eltern"), "eltern_frage": a.get("eltern_frage"),
         "einheiten": [w for w in a.get("einheiten") or [] if w in vorhanden]}
        for a in (achsen or [])
    ] or [{"id": None, "frage": None, "eltern": None, "eltern_frage": None,
           "einheiten": list(vorhanden)}]

    achse_von = {w: g["id"] for g in gruppen for w in g["einheiten"]}

    kinder: dict[str, list[str]] = {wid: [] for wid in vorhanden}
    wurzeln_je_gruppe: dict[Any, list[str]] = {g["id"]: [] for g in gruppen}
    for g in gruppen:
        for wid in g["einheiten"]:
            # Ein Elternknoten aus einer anderen Achse haengt den Knoten aus
            # seiner Gruppe aus. Dann ist er hier Wurzel, und der Bezug bleibt
            # als ``auch_unter`` sichtbar.
            eltern = [v for v in voraus[wid] if achse_von.get(v) == g["id"]]
            if eltern:
                kinder[eltern[0]].append(wid)
            else:
                wurzeln_je_gruppe[g["id"]].append(wid)

    def knoten(wid: str, tiefe: int = 0) -> dict[str, Any]:
        w = vorhanden[wid]
        belege = [k["von"] for k in rueckwaerts(db, wid, "stuetzt")]
        lektion = db.execute(
            "SELECT lektion_id FROM lektion_einheiten WHERE einheit_id = ? ORDER BY rang",
            (wid,),
        ).fetchone()
        eintrag: dict[str, Any] = {
            "id": f"N-{wid}",
            "label": (w["stichwort"] or "").strip() or w["titel"],
            # Die Behauptung bleibt erreichbar, sie steht nur nicht im Knoten.
            "satz": w["titel"],
            "art": "begriff",
            "wissenseinheit": wid,
            "lektion": lektion["lektion_id"] if lektion else None,
            "grad": w["grad"],
            "kurzfassung": w["kurzfassung"],
            "belege": belege,
            "kinder": [] if tiefe > 12 else [knoten(k, tiefe + 1) for k in kinder[wid]],
        }
        weitere = voraus[wid][1:]
        if weitere:
            eintrag["auch_unter"] = weitere
        quer = [k["nach"] for k in vorwaerts(db, wid, "siehe_auch")]
        if quer:
            eintrag["querbezug"] = quer  # MMP-5
        return eintrag

    if not achsen:
        return [knoten(w) for w in wurzeln_je_gruppe[gruppen[0]["id"]]]

    achsknoten = [
        {
            "id": f"N-achse-{g['id']}",
            "label": g["frage"],
            "art": "achse",
            "kinder": [knoten(w) for w in wurzeln_je_gruppe[g["id"]]],
            "eltern": g.get("eltern"),
            "eltern_frage": g.get("eltern_frage"),
        }
        for g in gruppen
        if wurzeln_je_gruppe[g["id"]]
    ]

    # **Zwei Ebenen bleiben zwei Ebenen** (MMP-10a). Bis zum 13.09.2026 hingen
    # alle Achsen gleichrangig an der Wurzel. Bei K-01 waren das 39 Fragen
    # nebeneinander — eine Stichpunktliste mit Kurven dazwischen, also genau
    # das, wogegen E-24 geschrieben wurde.
    #
    # Die Reihenfolge der Elternachsen folgt dem ersten Auftreten ihrer
    # Unterachsen, nicht einer neuen Sortierung: Der Rang kommt aus der
    # Analyse, hier wird nur gruppiert.
    if not any(k["eltern"] for k in achsknoten):
        for k in achsknoten:
            k.pop("eltern", None)
            k.pop("eltern_frage", None)
        return achsknoten

    oben: list[dict[str, Any]] = []
    nach_id: dict[Any, dict[str, Any]] = {}
    for k in achsknoten:
        eltern = k.pop("eltern", None)
        frage = k.pop("eltern_frage", None)
        if not eltern:
            oben.append(k)
            continue
        if eltern not in nach_id:
            nach_id[eltern] = {
                "id": f"N-achse-{eltern}",
                "label": frage or eltern,
                "art": "achse",
                "kinder": [],
            }
            oben.append(nach_id[eltern])
        nach_id[eltern]["kinder"].append(k)
    return oben


# --------------------------------------------------------------------------
# BIB-20 — was veraltet, wenn sich hier etwas aendert
# --------------------------------------------------------------------------


def kette_abwaerts(db: sqlite3.Connection, knoten: str) -> dict[str, list[str]]:
    """Alle Knoten, die von ``knoten`` abhaengen, nach Art sortiert."""
    gesehen = {knoten}
    rand = [knoten]
    nach_art: dict[str, list[str]] = {}
    while rand:
        aktuell = rand.pop()
        for typ, richtung in _WEITERGABE:
            if richtung == "vor":
                kanten = vorwaerts(db, aktuell, typ)
                nachbarn = [(k["nach"], k["nach_art"]) for k in kanten]
            else:
                kanten = rueckwaerts(db, aktuell, typ)
                nachbarn = [(k["von"], k["von_art"]) for k in kanten]
            for ziel, art in nachbarn:
                if ziel in gesehen:
                    continue
                gesehen.add(ziel)
                rand.append(ziel)
                nach_art.setdefault(art, []).append(ziel)
    for liste in nach_art.values():
        liste.sort()
    return nach_art


def veraltet_durch(db: sqlite3.Connection, knoten: str) -> dict[str, Any]:
    """BIB-20: Welche Artefakte veralten, wenn sich ``knoten`` aendert?

    ``knoten`` darf eine Quelle, eine Quellenversion, eine Fundstelle, ein
    Beleg oder eine Wissenseinheit sein. Die Wirkung laeuft die Evidenzkette
    abwaerts bis zu den erzeugten Artefakten.
    """
    betroffen = kette_abwaerts(db, knoten)
    einheiten = list(betroffen.get("einheit", []))
    # Ist der Ausgang selbst eine Wissenseinheit, gehoert er dazu: Wer WE-0001
    # aendert, macht die Lektion veraltet, die WE-0001 verwendet — auch wenn
    # keine weitere Einheit betroffen ist (BIB-20).
    if knoten.startswith("WE-") and knoten not in einheiten:
        einheiten.append(knoten)

    lektionen: list[str] = []
    if einheiten:
        rows = db.execute(
            "SELECT DISTINCT lektion_id FROM lektion_einheiten WHERE einheit_id IN (%s)"
            % ",".join("?" * len(einheiten)),
            einheiten,
        )
        lektionen = sorted(r["lektion_id"] for r in rows)

    # Einheiten, die die geaenderte *voraussetzen*: nicht falsch geworden,
    # aber in der Leseordnung betroffen (BIB-12). Bewusst getrennt gefuehrt.
    nachgelagert = sorted(
        k["von"] for k in rueckwaerts(db, knoten, "setzt_voraus")
    )

    ergebnis: dict[str, Any] = {
        "ausgang": knoten,
        "belege": betroffen.get("beleg", []),
        "fundstellen": betroffen.get("fundstelle", []),
        "versionen": betroffen.get("version", []),
        "einheiten": einheiten,
        "lektionen": lektionen,
        "artefakte": lektionen,
        "nachgelagerte_einheiten": nachgelagert,
    }
    if not lektionen:
        ergebnis["_fehlt"] = (
            "Es gibt keine Lektionsschicht in der Bibliothek (BIB-26/27), also "
            "auch keine erzeugten Artefakte, die veralten koennten. Sobald "
            "Lektionsdateien existieren, beantwortet dieselbe Abfrage die Frage "
            "vollstaendig."
        )
    return ergebnis
