"""Index und Abfragen gegen das echte Material (BIB-18b, BIB-20 bis BIB-24)."""

from __future__ import annotations

from bibliothek import abfragen
from bibliothek.index import baue_index, oeffne


def test_index_traegt_alles(db, bibliothek):
    meta = abfragen.meta(db)
    assert int(meta["quellen"]) == len(bibliothek.quellen)
    assert int(meta["belege"]) == len(bibliothek.belege)
    assert int(meta["einheiten"]) == len(bibliothek.einheiten)
    assert meta["gebaut_am"]


def test_index_wird_immer_neu_gebaut(wissen, tmp_path):
    """BIB-18b: kein inkrementeller Bau, keine Migration, Wegwerfware."""
    ziel = tmp_path / "index.db"
    baue_index(wissen, ziel)
    erste = oeffne(ziel)
    vorher = abfragen.meta(erste)
    groesse = ziel.stat().st_size
    erste.close()

    baue_index(wissen, ziel)
    zweite = oeffne(ziel)
    nachher = abfragen.meta(zweite)
    anzahl = zweite.execute("SELECT count(*) FROM belege").fetchone()[0]
    zweite.close()

    assert ziel.stat().st_size == groesse, "zweiter Bau ergab eine andere Datei"
    assert nachher["belege"] == vorher["belege"] == str(anzahl)
    assert nachher["gebaut_am"] >= vorher["gebaut_am"]
    assert not (tmp_path / "index.db.neu").exists(), "die Baustelle blieb liegen"


def test_kanten_sind_typisiert(db):
    """BIB-22: Ein untypisierter Verweis ist keine Kante."""
    typen = {r["typ"] for r in db.execute("SELECT DISTINCT typ FROM kanten")}
    assert typen
    assert all(t.strip() for t in typen)
    assert "stuetzt" in typen
    assert "setzt_voraus" in typen
    leer = db.execute("SELECT count(*) FROM kanten WHERE typ IS NULL OR typ = ''").fetchone()[0]
    assert leer == 0


def test_kanten_tragen_gueltigkeit(db):
    """BIB-23: Kanten, die von einem Beleg ausgehen, erben dessen Angaben."""
    for r in db.execute("SELECT * FROM kanten WHERE typ = 'stuetzt' LIMIT 20"):
        beleg = db.execute("SELECT * FROM belege WHERE id = ?", (r["von"],)).fetchone()
        assert r["gilt_ab"] == beleg["gilt_ab"]
        assert r["zuversicht"] == beleg["zuversicht"]
        assert r["gesetzt_von"], "ohne Herkunft ist BIB-23 nicht erfuellt"
        assert r["erklaert_in"], "die Datei, die die Kante erklaert, fehlt"


def test_fremde_kantentypen_sind_markiert(db):
    """Typen auszerhalb BIB-22 werden gebaut, aber nicht als BIB-22 ausgegeben."""
    fremd = {r["typ"] for r in db.execute("SELECT DISTINCT typ FROM kanten WHERE bib22 = 0")}
    eigen = {r["typ"] for r in db.execute("SELECT DISTINCT typ FROM kanten WHERE bib22 = 1")}
    assert "siehe_auch" in fremd
    assert not (fremd & eigen)


def test_rueckwaertskante(db):
    """Die Frage, fuer die es den Index gibt: Wer zeigt auf mich?"""
    stuetzen = abfragen.rueckwaerts(db, "WE-0194", "stuetzt")
    assert {k["von"] for k in stuetzen} == {"B-0043-03", "B-0043-02"}
    voraus = abfragen.rueckwaerts(db, "WE-0194", "setzt_voraus")
    assert {k["von"] for k in voraus} >= {"WE-0195"}


def test_volltextsuche_findet_in_allen_dreien(db):
    treffer = abfragen.suche(db, "DataZone", grenze=30)
    arten = {t["art"] for t in treffer}
    assert "aussagen" in arten
    assert "zitate" in arten
    assert treffer == sorted(treffer, key=lambda t: t["rang"])
    nur = abfragen.suche(db, "Verarbeitungsort", arten=["einheiten"], grenze=5)
    assert all(t["art"] == "einheiten" for t in nur)


def test_volltextsuche_faellt_bei_wirrem_ausdruck_nicht_um(db):
    for wirr in ('AND', '"', 'a*b:c', ')('):
        abfragen.suche(db, wirr, grenze=3)  # kein Absturz, Ergebnis darf leer sein


def test_beleg_aufloesen_zieht_die_ganze_kette(db):
    """Beleg → Fundstelle → Quellenversion → Quelle (BIB-21, Evidenzgraph)."""
    b = abfragen.beleg(db, "B-0048-05")
    assert b["aussage"].startswith("Für den technischen Wechselvorgang")
    assert "30 calendar" in b["zitat"]
    assert b["stelle"] == "Art. 25 Abs. 2 Buchst. a"
    assert b["quelle"]["id"] == "Q-0048"
    assert b["quelle"]["fundort"].startswith("http")
    assert b["quelle"]["abgerufen"]
    assert b["zuversicht"] in ("hoch", "mittel", "gering", "niedrig")
    assert abfragen.beleg(db, "B-9999-99") is None


def test_belege_ausgeschrieben_verschweigt_keine_luecke(db):
    aus = abfragen.belege_ausgeschrieben(db, ["B-0048-07", "B-9999-99", "B-0048-07"])
    assert set(aus) == {"B-0048-07", "B-9999-99"}
    assert aus["B-0048-07"]["zitat"]
    assert aus["B-0048-07"]["quelle_id"] == "Q-0048"
    assert aus["B-9999-99"]["fehlt"] is True


def test_bib20_quelle_aendert_sich(db):
    """BIB-20: Was veraltet, wenn diese Quelle sich aendert?"""
    r = abfragen.veraltet_durch(db, "Q-0048")
    # Die Demo sichert keine Volltexte (Lizenz); die Fundstellen haengen dann
    # direkt an der Quelle, und die Kette reisst trotzdem nicht ab.
    assert len(r["fundstellen"]) > 5
    assert "B-0048-05" in r["belege"]
    assert "WE-0217" in r["einheiten"]
    # BIB-20 sagt, welche Lektion veraltet, wenn diese Quelle sich aendert.
    assert "L-H6" in r["artefakte"], "die Lektion haengt an Q-0048"


def test_bib20_einheit_aendert_sich(db):
    r = abfragen.veraltet_durch(db, "WE-0194")
    # BIB-20: Aendert sich die Einheit, ist die Folge neu zu bauen.
    assert "L-H1" in r["artefakte"]
    assert set(r["nachgelagerte_einheiten"]) >= {"WE-0195"}


def test_begriffsbaum_liest_die_ordnung_ab(db):
    ids = [r["id"] for r in db.execute("SELECT id FROM einheiten ORDER BY id")]
    baum = abfragen.begriffsbaum(db, ids)
    assert baum, "kein Wurzelknoten"
    gefunden: set[str] = set()

    def gehe(knoten):
        for k in knoten:
            gefunden.add(k["wissenseinheit"])
            assert k["label"], k["id"]
            assert k["belege"], f"{k['id']} ohne Belege (BIB-11)"
            gehe(k["kinder"])

    gehe(baum)
    assert gefunden == set(ids), "der Baum verliert Einheiten"
    wurzeln = {k["wissenseinheit"] for k in baum}
    assert "WE-0194" in wurzeln  # setzt nichts voraus
    kinder = {
        k["wissenseinheit"] for k in next(b for b in baum if b["wissenseinheit"] == "WE-0194")["kinder"]
    }
    assert kinder == {"WE-0195"}


def test_befunde_liegen_im_index(db):
    """Die Abweichungen stehen im Index (`GET /api/zustand`).

    Kommt eine neue dazu, faellt dieser Test — dann gehoert sie ins
    Material oder in die Liste hier, statt stillschweigend durchzurutschen.
    """
    alle = abfragen.befunde(db)
    assert alle
    assert not abfragen.befunde(db, "fehler")
    erwartet = {
        "id_doppelt",
        "reichweite_fehlt",
        "versions_id_nicht_global",
        "kapitelschicht_ohne_id",
        "lektion_ohne_lernpfad_feld",
        "kapitel_ohne_lektion",
                "nichts_freigegeben",
        "kantentyp_ausserhalb_bib22",
        "kantentypen_ausserhalb_bib22",
        "gilt_bis_nirgends",
        "zuversicht_nur_am_beleg",
        "titel_ist_satz",
        "strittig_ohne_feld",
        # Dazugekommen am 13.09.2026.
        # Sie waren vorher schon da und nur nicht gemeldet.
        "absatz_ohne_marker",
        "version_fehlt",
        "version_unbekannt",
        "lektion_unvollstaendig",
        "lektion_ohne_kapitelmarken",
        "einheit_ohne_lektion",
    }
    arten = {f["art"] for f in alle}
    assert arten <= erwartet, f"neue Abweichung: {arten - erwartet}"
    assert "version_fehlt" in arten  # die Demo sichert keine Volltexte (Lizenz)
