"""Der Lernstand als eigene Wahrheit (OBF-7, R-3, R-4)."""

from __future__ import annotations

import pytest

from dienst.lernstand import Lernstand


def test_leerer_stand(lernstand):
    assert lernstand.alle() == {}
    assert lernstand.fortschritt("L-001") is None
    assert lernstand.einstellungen() == {"tempo": 1.0}


def test_zwei_achsen_statt_leiter(lernstand):
    """R-4: fragen: fertig ohne gehoert ist erlaubt und gewollt."""
    lernstand.setze("L-001", 0, "fertig")
    stand = lernstand.fortschritt("L-001")
    assert stand["position_sek"] == 0
    assert stand["fragen"] == "fertig"


def test_ungueltiger_fragenzustand(lernstand):
    with pytest.raises(ValueError):
        lernstand.setze("L-001", 10, "halbfertig")
    with pytest.raises(ValueError):
        lernstand.setze("L-001", -1, "offen")


def test_spaeterer_zeitpunkt_gewinnt(lernstand):
    lernstand.setze("L-007", 200, "offen", zeitpunkt="2026-09-11T09:00:00+02:00")
    ergebnis = lernstand.setze("L-007", 100, "offen", zeitpunkt="2026-09-11T08:00:00+02:00")
    assert ergebnis["uebernommen"] is False
    assert lernstand.fortschritt("L-007")["position_sek"] == 200


def test_zonen_werden_verglichen_nicht_buchstabiert(lernstand):
    """08:00+02:00 ist spaeter als 07:30+00:00 — als Text sortiert es umgekehrt."""
    lernstand.setze("L-008", 10, "offen", zeitpunkt="2026-09-11T07:30:00+00:00")
    ergebnis = lernstand.setze("L-008", 20, "offen", zeitpunkt="2026-09-11T09:45:00+02:00")
    assert ergebnis["uebernommen"] is True
    assert lernstand.fortschritt("L-008")["position_sek"] == 20


def test_lernstand_ueberlebt_den_index(lernstand):
    """OBF-7: Der Index ist Wegwerfware, der Lernstand nicht."""
    lernstand.setze("L-001", 42, "teilweise")
    wieder = Lernstand(lernstand.pfad)
    assert wieder.fortschritt("L-001")["position_sek"] == 42


def test_tempo_bleibt(lernstand):
    lernstand.setze_einstellung("tempo", "1.25")
    assert lernstand.einstellungen()["tempo"] == 1.25
