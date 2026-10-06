"""Der Leser gegen das echte Material (BIB-18, E-9)."""

from __future__ import annotations

from bibliothek.lesen import BIB22_TYPEN
from bibliothek.yaml_min import YamlFehler, lies_block, trenne_frontmatter


def test_alles_gelesen(bibliothek):
    assert bibliothek.quellen, "keine Quellen gelesen"
    assert bibliothek.fundstellen, "keine Fundstellen gelesen"
    assert bibliothek.belege, "keine Belege gelesen"
    assert bibliothek.einheiten, "keine Wissenseinheiten gelesen"
    assert bibliothek.pfade, "kein Lernpfad gelesen"


def test_keine_lesefehler(bibliothek):
    """Fehler sind nicht dasselbe wie Abweichungen.

    Abweichungen (Spec gegen Material) sind erwartet und werden gemeldet.
    Ein *Fehler* heiszt: Eine Datei liess sich nicht lesen oder ein Verweis
    zeigt ins Leere. Davon darf es keinen geben.
    """
    fehler = [f for f in bibliothek.befunde if f.schwere == "fehler"]
    assert fehler == [], "\n".join(f"{f.art} [{f.betrifft}] {f.text}" for f in fehler)


def test_jeder_beleg_haengt_an_einer_fundstelle(bibliothek):
    """BIB-7: Ein Beleg ohne Fundstelle ist unvollstaendig."""
    for beleg in bibliothek.belege.values():
        assert beleg.fundstelle_id, beleg.id
        assert beleg.fundstelle_id in bibliothek.fundstellen, beleg.id


def test_aussage_und_zitat_sind_getrennt(bibliothek):
    """BIB-8: Der Wortlaut steht an der Fundstelle, die Deutung am Beleg."""
    for beleg in bibliothek.belege.values():
        fundstelle = bibliothek.fundstellen[beleg.fundstelle_id]
        assert beleg.aussage.strip(), beleg.id
        assert fundstelle.zitat.strip(), fundstelle.id
        assert beleg.aussage.strip() != fundstelle.zitat.strip(), beleg.id


def test_einheiten_nennen_nur_vorhandene_belege(bibliothek):
    """BIB-11: Jede Aussage belegt — und der Beleg muss es geben."""
    for we in bibliothek.einheiten.values():
        assert we.belegt_durch, we.id
        for bid in we.belegt_durch:
            assert bid in bibliothek.belege, f"{we.id} → {bid}"


def test_einheit_hat_kurzfassung_inhalt_prueffrage(bibliothek):
    """BIB-10 plus der Zuschnitt aus eingang/M-001/AUFTRAG.md."""
    for we in bibliothek.einheiten.values():
        assert we.kurzfassung.strip(), we.id
        assert we.inhalt.strip(), we.id
        assert we.prueffrage.strip(), we.id


def test_lernpfad_hat_abschnitte(bibliothek):
    pfad = bibliothek.pfade["P-02"]
    assert pfad.titel
    assert len(pfad.abschnitte) == 8
    schluessel = [a.schluessel for a in pfad.abschnitte]
    assert schluessel == sorted(schluessel), "Abschnitte sind nicht in Reihenfolge"
    for a in pfad.abschnitte:
        assert a.titel.strip(), a.schluessel


def test_die_gemeldeten_abweichungen_sind_die_erwarteten(bibliothek):
    """Die Abweichungen sind bekannt und stehen im Index (`befunde`).

    Der Test haelt sie fest: Taucht eine neue auf, faellt er — dann ist
    entweder das Material gewachsen oder die Spec eingeloest worden, und
    beides gehoert ins Protokoll statt stillschweigend durchzurutschen.
    """
    erwartet = {
        "id_doppelt",
        "reichweite_fehlt",
        "versions_id_nicht_global",
        "kapitelschicht_ohne_id",
        # 11.09.2026: `lektionsschicht_fehlt` ist weg — die erste Lektion
        # (L-F01) ist aus dem ersten echten Podcastlauf entstanden. Dafuer
        # zwei neue, beide erwartet:
        "lektion_ohne_lernpfad_feld",   # pfad_id wird aus dem Kapitel erschlossen
        "kapitel_ohne_lektion",         # 12 der 13 Abschnitte haben noch keine
        "nichts_freigegeben",
        "kantentyp_ausserhalb_bib22",
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
    gefunden = {f.art for f in bibliothek.befunde}
    assert gefunden <= erwartet, f"neue Abweichung: {gefunden - erwartet}"


def test_spaeterer_auftrag_verdraengt_frueheren(wissen, tmp_path):
    """Vergeben zwei Auftraege dieselbe ID, gilt der spaetere — und es wird gemeldet.

    So entsteht eine Nachpruefung: Ein zweiter Rechercheauftrag liest dieselbe
    Quelle am Volltext nach und ueberschreibt den Beleg des ersten.
    """
    import shutil
    from bibliothek.lesen import lies_bibliothek
    kopie = tmp_path / "wissen"
    shutil.copytree(wissen, kopie, ignore=shutil.ignore_patterns("audio", "bilder"))
    spaeter = kopie / "eingang" / "A-099" / "belege"
    spaeter.mkdir(parents=True)
    alt = (kopie / "eingang" / "A-008" / "belege" / "B-0043-01.md").read_text()
    spaeter.joinpath("B-0043-01.md").write_text(alt.replace("zuversicht: hoch", "zuversicht: mittel"))
    bib = lies_bibliothek(kopie)
    assert [f for f in bib.befunde if f.art == "id_doppelt"]
    assert bib.belege["B-0043-01"].herkunft == "A-099"


# -- yaml_min ---------------------------------------------------------------


def test_yaml_min_liest_die_bekannten_formen():
    block, rumpf = trenne_frontmatter(
        "---\n"
        "id: WE-0001\n"
        "belegt_durch: [B-0002-01, B-0001-06]\n"
        "leer: []\n"
        "gefaltet: >\n"
        "  eine Zeile\n"
        "  und noch eine\n"
        "liste:\n"
        "  - eins\n"
        "  - zwei\n"
        "---\n"
        "Rumpf\n"
    )
    kopf = lies_block(block)
    assert kopf["id"] == "WE-0001"
    assert kopf["belegt_durch"] == ["B-0002-01", "B-0001-06"]
    assert kopf["leer"] == []
    assert kopf["gefaltet"] == "eine Zeile und noch eine"
    assert kopf["liste"] == ["eins", "zwei"]
    assert rumpf.strip() == "Rumpf"


def test_yaml_min_raet_nicht():
    """Was der Leser nicht kennt, wirft er — statt etwas Plausibles zu liefern."""
    # `flow: {a: 1}` steht hier nicht mehr: Seit L-F01 traegt das Frontmatter
    # `stimmen: {MODERATOR: shimmer, GAST: onyx}`, und der Leser kann flache
    # Inline-Abbildungen. Verschachtelt bleibt verboten.
    for kaputt in ("verschachtelt:\n  a: 1\n", "kein doppelpunkt\n",
                   "tief: {a: {b: 1}}\n"):
        try:
            lies_block(kaputt)
        except YamlFehler:
            continue
        raise AssertionError(f"haette werfen muessen: {kaputt!r}")


def test_bib22_vokabular_ist_das_aus_der_spec():
    assert BIB22_TYPEN == {
        "stuetzt", "widerspricht", "praezisiert", "ersetzt",
        "handelt_von", "setzt_voraus", "dient_lernziel", "prueft",
    }
