"""Der Gesprächspartner erinnert sich über Sitzungen hinweg (R-16, DIS-30).

Rückmeldung vom 11.09.2026: „ich wollte vor allem schauen, ob er bei Restart noch weiß,
worüber wir gesprochen haben." Konnte er nicht — der Ton läuft direkt vom
Browser zum Anbieter (E-20a), der Server hörte nie mit, und es gab nichts, woraus
er sich hätte erinnern können.
"""

from __future__ import annotations

import pytest

from dienst.lernstand import Lernstand


@pytest.fixture()
def stand(tmp_path):
    return Lernstand(tmp_path / "lernstand.db")


def test_mitschrift_ueberlebt_die_sitzung(stand):
    stand.merke_beitraege("S-1", "K-01", [
        {"rolle": "partner", "text": "Woran erkennst du eine Verzerrung?"},
        {"rolle": "lernender", "text": "Wenn das Urteil beim Tauschen kippt."},
    ])
    verlauf = stand.verlauf("S-1")
    assert [b["rolle"] for b in verlauf] == ["partner", "lernender"]
    assert verlauf[0]["kapitel_id"] == "K-01"


def test_unbrauchbare_beitraege_fallen_weg(stand):
    gemerkt = stand.merke_beitraege("S-1", "K-01", [
        {"rolle": "partner", "text": "   "},          # leer
        {"rolle": "publikum", "text": "dazwischen"},  # keine bekannte Rolle
        {"rolle": "lernender", "text": "richtig"},
    ])
    assert gemerkt == 1
    assert len(stand.verlauf("S-1")) == 1


def test_frueheres_gespraech_kommt_in_den_naechsten_prompt(stand):
    """Das ist der Punkt: neue Sitzung, altes Wissen."""
    stand.merke_beitraege("S-1", "K-01", [
        {"rolle": "lernender", "text": "Position Bias verstehe ich jetzt."},
    ])
    frueher = stand.sitzungen_zum_kapitel("K-01")
    assert len(frueher) == 1
    assert frueher[0]["beitraege"][0]["text"] == "Position Bias verstehe ich jetzt."


def test_gedaechtnis_ist_gedeckelt(stand):
    """Ein Prompt, der jedes je gesprochene Wort mitschleppt, wird unbrauchbar."""
    for n in range(6):
        stand.merke_beitraege(f"S-{n}", "F", [{"rolle": "lernender", "text": f"Satz {n}"}])
    frueher = stand.sitzungen_zum_kapitel("F", grenze=3)
    assert [s["sitzung_id"] for s in frueher] == ["S-3", "S-4", "S-5"], "jüngste zuletzt"


def test_fremdes_kapitel_bleibt_draussen(stand):
    stand.merke_beitraege("S-1", "K-01", [{"rolle": "lernender", "text": "zu K-01"}])
    stand.merke_beitraege("S-2", "K-02", [{"rolle": "lernender", "text": "zu K-02"}])
    assert len(stand.sitzungen_zum_kapitel("K-01")) == 1
    assert stand.sitzungen_zum_kapitel("K-01")[0]["sitzung_id"] == "S-1"
