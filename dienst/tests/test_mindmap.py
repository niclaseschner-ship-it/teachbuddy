"""Die Mindmap trägt Stichworte und Achsen (MMP-3, MMP-10, E-24).

Bis zum 11.09.2026 standen die Behauptungen der Wissenseinheiten als
Knotenbeschriftung im Bild — ganze Sätze in Kästen. Der Mangel war bekannt und
wurde in der App *erklärt* statt behoben. Diese Tests halten fest, dass er
behoben ist.
"""

from __future__ import annotations

from bibliothek import abfragen
from bibliothek.yaml_min import lies_block


def test_knoten_tragen_stichworte_und_nicht_die_behauptung(db):
    """MMP-3: Ein Knoten trägt ein Stichwort, keinen Satz."""
    analyse = _analyse(db, "K-03")
    baum = abfragen.begriffsbaum(db, _einheiten(db, "K-03"), analyse["achsen"])
    begriffe = [k for k in _flach(baum) if k["art"] == "begriff"]
    assert begriffe, "ohne Begriffe prüft der Test nichts"
    for k in begriffe:
        assert len(k["label"].split()) <= 4, (k["label"], "höchstens vier Wörter")
        # Die Behauptung geht nicht verloren, sie steht nur nicht im Kasten.
        assert k["satz"], k["label"]
        assert k["satz"] != k["label"]


def test_achsen_gliedern_und_lassen_nichts_liegen(db):
    """MMP-10: jede Einheit an genau einer Achse, keine fällt weg."""
    we_ids = _einheiten(db, "K-03")
    analyse = _analyse(db, "K-03")
    baum = abfragen.begriffsbaum(db, we_ids, analyse["achsen"])

    achsen = [k for k in baum if k["art"] == "achse"]
    # MMP-10a: Die Zahl richtet sich nach dem Kapitel, die Breite ist
    # begrenzt — eine flache Liste aus 39 Fragen war bis zum 13.09.2026 der
    # Fehler, nicht das Ziel.
    assert len(achsen) >= 2, "eine einzige Achse ist keine Gliederung"
    assert len(achsen) <= 9, "mehr als neun Aeste liest niemand (MMP-10a)"

    def alle_achsen(knoten):
        for k in knoten:
            if k["art"] != "achse":
                continue
            yield k
            yield from alle_achsen(k.get("kinder") or [])

    for a in alle_achsen(baum):
        assert a["label"].endswith("?"), (a["label"], "eine Achse ist eine Frage")
        assert len(a.get("kinder") or []) <= 9, (a["label"], "zu breit (MMP-10a)")

    # MMP-10a: zwei Ebenen Achsen, keine dritte.
    def achsentiefe(knoten, t=0):
        """Wie viele Achsen-Ebenen tief. Begriffe zaehlen nicht mit."""
        tief = t
        for k in knoten:
            if k["art"] == "achse":
                tief = max(tief, achsentiefe(k.get("kinder") or [], t + 1))
        return tief

    assert 1 <= achsentiefe(baum) <= 2, "hoechstens zwei Achsen-Ebenen (MMP-10a)"

    gefunden = [k["wissenseinheit"] for k in _flach(baum) if k["art"] == "begriff"]
    assert sorted(gefunden) == sorted(we_ids), "keine Einheit doppelt, keine fehlt"


def test_ohne_analyse_wird_keine_gliederung_erfunden(db):
    """Eine geratene Gliederung wäre schlimmer als keine."""
    baum = abfragen.begriffsbaum(db, _einheiten(db, "K-03"), None)
    assert baum, "ohne Analyse bleibt der Voraussetzungsbaum"
    assert not [k for k in _flach(baum) if k["art"] == "achse"]


def test_yaml_liest_abbildungen_in_listen():
    """Der Minimalleser muss die Form der Analysedatei können."""
    kopf = lies_block(
        "kapitel: F\n"
        "achsen:\n"
        "  - id: A1\n"
        "    frage: Wer urteilt?\n"
        "    einheiten: [WE-0001, WE-0004]\n"
        "  - id: A2\n"
        "    frage: Was hilft?\n"
        "    einheiten: [WE-0003]\n",
        herkunft="test",
    )
    assert kopf["kapitel"] == "F"
    assert [a["id"] for a in kopf["achsen"]] == ["A1", "A2"]
    assert kopf["achsen"][0]["einheiten"] == ["WE-0001", "WE-0004"]
    assert kopf["achsen"][1]["frage"] == "Was hilft?"


# -- Hilfen ----------------------------------------------------------------

def _einheiten(db, kapitel: str) -> list[str]:
    return [
        r["einheit_id"]
        for r in db.execute(
            "SELECT DISTINCT le.einheit_id FROM lektion_einheiten le"
            " JOIN lektionen l ON l.id = le.lektion_id WHERE l.kapitel = ?",
            (kapitel,),
        )
    ]


def _analyse(db, kapitel: str) -> dict:
    achsen = [
        {
            "id": a["achse_id"],
            "frage": a["frage"],
            # MMP-10a. Fehlt das hier, faellt der Baum in die flache Fassung
            # zurueck und der Test prueft etwas anderes als der Dienst liefert
            # — genau so ist er am 13.09.2026 auf 39 Achsen gelaufen.
            "eltern": a["eltern"],
            "eltern_frage": a["eltern_frage"],
            "einheiten": [
                r["einheit_id"]
                for r in db.execute(
                    "SELECT einheit_id FROM mindmap_achse_einheiten"
                    " WHERE kapitel = ? AND achse_id = ? ORDER BY rang",
                    (kapitel, a["achse_id"]),
                )
            ],
        }
        for a in db.execute(
            "SELECT * FROM mindmap_achsen WHERE kapitel = ? ORDER BY rang", (kapitel,)
        )
    ]
    assert achsen, f"Kapitel {kapitel} hat keine Strukturanalyse"
    return {"achsen": achsen}


def _flach(knoten, sammler=None):
    sammler = [] if sammler is None else sammler
    for k in knoten:
        sammler.append(k)
        _flach(k.get("kinder") or [], sammler)
    return sammler
