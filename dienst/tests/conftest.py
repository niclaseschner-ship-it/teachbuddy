"""Gemeinsame Vorrichtungen. Alle Tests laufen gegen das **echte** Material
in ``demo/`` — kein Fixture-Repo, keine erfundenen Beispieldateien, die die
Abweichungen glattbuegeln, um derentwillen es die Tests gibt.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parents[2]
if str(WURZEL) not in sys.path:
    sys.path.insert(0, str(WURZEL))

WISSEN = (WURZEL / "demo").resolve()

from bibliothek.index import baue_index, oeffne  # noqa: E402
from bibliothek.lesen import lies_bibliothek  # noqa: E402
from dienst.app import erzeuge_app  # noqa: E402
from dienst.lernstand import Lernstand  # noqa: E402

pytestmark = pytest.mark.skipif(not WISSEN.is_dir(), reason="demo/ fehlt")

ARBEIT = WURZEL / "arbeit" / "pytest"


def pytest_configure(config: pytest.Config) -> None:
    """APP-11: Testdateien unter ``arbeit/pytest``, nicht im System-Temp.

    Auf kleinen Geraeten ist ``/tmp`` oft ein RAM-Dateisystem, und ein Index
    von ein paar Megabyte je Lauf gehoert nicht dorthin. Steht die Basis schon
    auf der Befehlszeile, bleibt sie stehen.

    Gesetzt wird das hier und nicht in einer ``pytest.ini`` im
    Wurzelverzeichnis: Die laege auszerhalb von ``bibliothek/`` und
    ``dienst/`` und wuerde dem Nachbarn in ``podcast/`` die Sammelpfade
    vorschreiben.
    """
    if not config.option.basetemp:
        ARBEIT.mkdir(parents=True, exist_ok=True)
        config.option.basetemp = str(ARBEIT)


def _ueberspringen_wenn_kein_material() -> None:
    if not WISSEN.is_dir():
        pytest.skip(f"Echtes Material fehlt: {WISSEN}")


@pytest.fixture(scope="session")
def wissen() -> Path:
    _ueberspringen_wenn_kein_material()
    return WISSEN


@pytest.fixture(scope="session")
def bibliothek(wissen):
    return lies_bibliothek(wissen)


@pytest.fixture(scope="session")
def index_pfad(wissen, tmp_path_factory) -> Path:
    """Der Index wird fuer die Tests frisch gebaut — immer komplett (BIB-18b).

    ``tmp_path_factory`` legt unter der pytest-Basis an; die steht auf
    ``arbeit/pytest``, nicht im System-Temp (APP-11).
    """
    ziel = tmp_path_factory.mktemp("index") / "index.db"
    baue_index(wissen, ziel)
    return ziel


@pytest.fixture(scope="session")
def db(index_pfad):
    return oeffne(index_pfad)


@pytest.fixture
def lernstand(tmp_path) -> Lernstand:
    return Lernstand(tmp_path / "lernstand.db")


@pytest.fixture
def klient(index_pfad, tmp_path):
    app = erzeuge_app(index_pfad, tmp_path / "lernstand.db")
    app.config.update(TESTING=True)
    return app.test_client()
