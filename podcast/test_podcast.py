"""Proben für den Podcast-Bauer.

Läuft ohne Netz, ohne Azure und ohne Agentenaufruf: Skript kommt aus einer
Datei, Vertonung aus `StilleVertonung`. ffmpeg wird **echt** benutzt — der
Schnitt ist die Stelle, an der ein Attrappen-Test nichts beweist.

    python3 -m pytest podcast/ -q
"""

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from podcast import bauen, belegprobe, einheiten, skript, vertonung  # noqa: E402

ECHTES_MATERIAL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "demo", "eingang", "M-016", "einheiten")

GUTES_SKRIPT = """# Wohin die Daten gehen

## Worum es geht

MODERATOR: Heute geht es darum, wo eine Anfrage eigentlich gerechnet wird. [E]
GAST: Der Reihe nach: Das hängt davon ab, welchen Bereitstellungstyp man
beim Einrichten wählt. [B-0043-03]

## Global oder Datenzone

MODERATOR: Und innerhalb der Zone, steht der Ort dann fest? [B-0043-02]
GAST: Nein, die Verarbeitung kann zwischen den Regionen wandern. [B-0043-02]
[B-0043-04]

## Zusammenfassung

MODERATOR: Halten wir fest. [E]
GAST: Gespeicherte Daten liegen verschlüsselt in der gewählten Region. [B-0043-05]
"""


def _einheiten():
    return einheiten.lies_verzeichnis(ECHTES_MATERIAL)


# --------------------------------------------------------------------------
# einheiten.py
# --------------------------------------------------------------------------

def test_liest_das_echte_material():
    liste = _einheiten()
    assert len(liste) == 31
    assert [e.id for e in liste] == ["WE-%04d" % n for n in range(194, 225)]
    we = next(e for e in liste if e.id == "WE-0215")
    assert "B-0047-02" in we.belege
    assert we.setzt_voraus == ("WE-0212", "WE-0214")
    assert we.quellen == ("0046", "0047")
    assert len(we.stand) == 16


def test_stand_haengt_am_inhalt(tmp_path):
    quelle = os.path.join(ECHTES_MATERIAL, "WE-0194.md")
    with open(quelle, encoding="utf-8") as f:
        roh = f.read()
    kopie = tmp_path / "WE-0194.md"
    kopie.write_text(roh, encoding="utf-8")
    assert einheiten.lies(str(kopie)).stand == einheiten.lies(quelle).stand
    kopie.write_text(roh + "\nein Satz mehr\n", encoding="utf-8")
    assert einheiten.lies(str(kopie)).stand != einheiten.lies(quelle).stand


def test_einheit_ohne_belege_wird_abgewiesen(tmp_path):
    datei = tmp_path / "WE-9999.md"
    datei.write_text(
        "---\nid: WE-9999\ntitel: Ohne\nbelegt_durch: []\n---\n\nText\n",
        encoding="utf-8")
    with pytest.raises(einheiten.EinheitFehler, match="belegt_durch"):
        einheiten.lies(str(datei))


def test_nur_schneidet_die_lektion_zu():
    # POD-3: Der Zuschnitt ist die Zeitspanne, nicht der Inhalt des Ordners.
    liste = einheiten.lies_verzeichnis(ECHTES_MATERIAL,
                                       nur=["WE-0197", "WE-0194"])
    assert [e.id for e in liste] == ["WE-0194", "WE-0197"]
    with pytest.raises(einheiten.EinheitFehler, match="WE-1234"):
        einheiten.lies_verzeichnis(ECHTES_MATERIAL, nur=["WE-1234"])


def test_belegregister_zeigt_auf_die_einheiten():
    register = einheiten.belegregister(_einheiten())
    assert register["B-0044-04"] == ["WE-0201"]
    # B-0043-02 tragen zwei Einheiten — beide müssen auflösbar sein.
    assert set(register["B-0043-02"]) == {"WE-0194", "WE-0195"}


# --------------------------------------------------------------------------
# skript.py — Form und Marker
# --------------------------------------------------------------------------

def test_liest_abschnitte_und_zeilen():
    s = skript.lies(GUTES_SKRIPT)
    assert s.titel == "Wohin die Daten gehen"
    assert [a.titel for a in s.abschnitte] == [
        "Worum es geht", "Global oder Datenzone", "Zusammenfassung"]
    assert [a.art for a in s.abschnitte] == [
        "einleitung", "inhalt", "zusammenfassung"]
    assert len(s.zeilen) == 6
    assert s.zeilen[0].sprecher == "MODERATOR"
    assert s.zeilen[1].belege == ("B-0043-03",)


def test_umbrochene_sprecherzeile_bleibt_eine_zeile():
    s = skript.lies(GUTES_SKRIPT)
    zeile = s.abschnitte[1].zeilen[1]
    assert zeile.sprecher == "GAST"
    assert zeile.belege == ("B-0043-02", "B-0043-04")
    assert "\n" not in zeile.sprechtext


def test_marker_verschwinden_vor_der_vertonung():
    # AUF-8c: sonst liest Azure "B 0002 01" mitten im Satz vor.
    roh = "Eine Erklärung. [B-0002-01] [B-0005-03]"
    assert skript.ohne_marker(roh) == "Eine Erklärung."
    assert skript.ohne_marker("Ein Satz [E] mit Einschub. [E]") == (
        "Ein Satz mit Einschub.")
    # Kein gültiger Marker → bleibt stehen, damit die Belegprobe ihn sieht.
    assert "[B-17]" in skript.ohne_marker("Behauptung. [B-17]")


def test_zeichenzahl_zaehlt_den_sprechtext():
    s = skript.lies(GUTES_SKRIPT)
    assert s.zeichen_sprechtext == sum(len(z.sprechtext) for z in s.zeilen)
    assert "[B-" not in "".join(z.sprechtext for z in s.zeilen)


def test_zu_wenige_abschnitte_scheitern():
    # POD-4: Eröffnung, Inhalt, Zusammenfassung.
    kurz = "# T\n\n## A\n\nGAST: Etwas. [E]\n\n## B\n\nGAST: Mehr. [E]\n"
    with pytest.raises(skript.SkriptFehler, match="POD-4"):
        skript.lies(kurz)


def test_ablehnung_wird_als_ablehnung_erkannt():
    # AUF-14: lieber eine ehrliche Absage als ein dünnes Artefakt.
    with pytest.raises(skript.Ablehnung, match="zu wenig"):
        skript.lies("# ABLEHNUNG\n\nDas Material ist zu wenig.\n")


def test_modell_und_fassung_stehen_in_der_kennung():
    # AUF-18. Codex schreibt seinen Kopf nach stderr, nicht nach stdout.
    kopf = ("Reading additional input from stdin...\n"
            "OpenAI Codex v0.142.0\n--------\nmodel: gpt-5.5\n")
    assert skript._modellkennung("/x/openai.chatgpt-26.616.71553/codex",
                                 kopf) == "codex 0.142.0 / gpt-5.5"
    assert skript._modellkennung("/x/openai.chatgpt-26.616.71553/codex", "") == (
        "codex 26.616.71553 / unbekannt")


def test_sprechanteile_zugunsten_des_gastes():
    s = skript.lies(GUTES_SKRIPT)
    anteile = s.sprechanteile()
    assert set(anteile) == {"MODERATOR", "GAST"}
    assert abs(sum(anteile.values()) - 1.0) < 1e-9
    assert anteile["GAST"] > anteile["MODERATOR"]


# --------------------------------------------------------------------------
# belegprobe.py — AUF-8b
# --------------------------------------------------------------------------

def test_gutes_skript_besteht():
    probe = belegprobe.pruefe(skript.lies(GUTES_SKRIPT), _einheiten())
    assert probe.bestanden, probe.bericht()
    assert "B-0043-03" in probe.belege_verwendet
    assert "WE-0194" in probe.einheiten_verwendet
    assert "WE-0198" in probe.einheiten_ungenutzt


def test_zeile_ohne_marker_laesst_scheitern():
    # Der wichtigste der drei Fälle: genau so sähe eine erfundene Passage aus.
    kaputt = GUTES_SKRIPT.replace(
        "MODERATOR: Und innerhalb der Zone, steht der Ort dann fest? [B-0043-02]",
        "MODERATOR: Und wie ist das bei Bildmodellen?")
    probe = belegprobe.pruefe(skript.lies(kaputt), _einheiten())
    assert not probe.bestanden
    assert [b.art for b in probe.befunde] == ["ohne-marker"]
    assert "Bildmodellen" in probe.befunde[0].text


def test_erfundener_beleg_laesst_scheitern():
    kaputt = GUTES_SKRIPT.replace("[B-0043-05]", "[B-9999-42]")
    probe = belegprobe.pruefe(skript.lies(kaputt), _einheiten())
    assert not probe.bestanden
    assert probe.befunde[0].art == "unaufloesbar"
    assert "B-9999-42" in probe.befunde[0].text


def test_beleg_auf_nicht_uebergebene_einheit_laesst_scheitern():
    # AUF-8b: ein Marker auf eine Einheit, die gar nicht übergeben wurde.
    nur_eine = [e for e in _einheiten() if e.id == "WE-0194"]
    probe = belegprobe.pruefe(skript.lies(GUTES_SKRIPT), nur_eine)
    arten = {b.art for b in probe.befunde}
    assert not probe.bestanden and arten == {"unaufloesbar"}


def test_beleghuelse_ohne_beleg_laesst_scheitern():
    kaputt = GUTES_SKRIPT.replace("[B-0043-03]", "[B-17]")
    probe = belegprobe.pruefe(skript.lies(kaputt), _einheiten())
    assert not probe.bestanden
    assert any(b.art == "kein-marker" for b in probe.befunde)


def test_quellenangabe_im_sprechtext_laesst_scheitern():
    # POD-5: im Audio wird nicht belegt.
    kaputt = GUTES_SKRIPT.replace(
        "GAST: Gespeicherte Daten liegen",
        "GAST: Laut Russinovich et al. liegen gespeicherte Daten")
    probe = belegprobe.pruefe(skript.lies(kaputt), _einheiten())
    assert not probe.bestanden
    assert any(b.art == "beleg-im-audio" for b in probe.befunde)


# --------------------------------------------------------------------------
# vertonung.py — echtes ffmpeg
# --------------------------------------------------------------------------

def test_stille_hat_die_bestellte_laenge(tmp_path):
    mp3 = vertonung.stille_mp3(1.5, arbeit=str(tmp_path))
    assert mp3[:3] in (b"ID3", b"\xff\xfb", b"\xff\xf3")
    assert abs(vertonung.dauer_sek(mp3, arbeit=str(tmp_path)) - 1.5) < 0.2


def test_zusammenfuegen_addiert_teile_und_pausen(tmp_path):
    tts = vertonung.StilleVertonung(str(tmp_path))
    teile = [
        vertonung.Teil(tts.synthese(text="ein zwei drei vier fünf", voice="onyx"),
                       pause_sek=0.55),
        vertonung.Teil(tts.synthese(text="sechs sieben acht", voice="shimmer"),
                       pause_sek=0.0),
    ]
    ziel = str(tmp_path / "folge.mp3")
    vertonung.fuege_zusammen(teile, ziel, arbeit=str(tmp_path))
    gesamt = vertonung.dauer_sek(ziel, arbeit=str(tmp_path))
    einzeln = sum(vertonung.dauer_sek(t.mp3, arbeit=str(tmp_path))
                  for t in teile)
    assert abs(gesamt - (einzeln + 0.55)) < 0.3


def test_zusammengefuegtes_audio_ist_sauber(tmp_path):
    # Die geerbte Erfahrung: nativer Concat zweier MP3-Streams gibt
    # DTS-Müll. Re-encode über libmp3lame — ffprobe muss die Datei am
    # Stück lesen können.
    tts = vertonung.StilleVertonung(str(tmp_path))
    teile = [vertonung.Teil(tts.synthese(text="a b c d e", voice="onyx"), 0.55)
             for _ in range(4)]
    ziel = str(tmp_path / "folge.mp3")
    vertonung.fuege_zusammen(teile, ziel, arbeit=str(tmp_path))
    lauf = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_name,sample_rate", "-of", "csv=p=0", ziel],
        capture_output=True, text=True, check=True)
    assert lauf.stdout.startswith("mp3,24000")
    assert lauf.stderr == ""


def test_azure_nur_eigene_variablen(monkeypatch):
    """Nur die TeachBuddy-Variablen zählen, damit Kosten trennbar bleiben (E-11a)."""
    for name in ("TEACHBUDDY_AZURE_OPENAI_ENDPOINT", "TEACHBUDDY_AZURE_OPENAI_KEY",
                 "TEACHBUDDY_AZURE_OPENAI_DEPLOYMENT"):
        monkeypatch.delenv(name, raising=False)
    # Eine fremde Variable zählt nicht.
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://egal")
    with pytest.raises(vertonung.TTSFehler, match="azure_endpoint"):
        vertonung.aus_umgebung()


def test_sprechtempo_geht_an_azure(monkeypatch):
    """Rückmeldung: „wir hatten auf Kinderhörbuch optimiert, es darf schneller sein."

    Das Tempo gehört in die Synthese, nicht nur in den Abspieler: Azure passt
    die Betonung an, ein beschleunigter Abspieler spielt nur schneller ab.
    """
    gesehen = {}

    class _FakeSpeech:
        def create(self, **kw):
            gesehen.update(kw)
            class _A:
                def read(self_inner): return b"\xff\xfb"
            return _A()

    class _FakeClient:
        def __init__(self, **_): self.audio = type("A", (), {"speech": _FakeSpeech()})()

    openai = pytest.importorskip("openai", reason="nur in der .venv installiert")
    monkeypatch.setattr(openai, "AzureOpenAI", _FakeClient, raising=False)
    v = vertonung.AzureVertonung(endpoint="e", api_key="k", deployment="d")
    v.synthese(text="Probe", voice="onyx")
    assert gesehen["speed"] == vertonung.SPRECHTEMPO
    assert vertonung.SPRECHTEMPO > 1.0, "Grundtempo soll über dem Hörspiel-Vorbild liegen"


def test_pausen_sind_straffer_als_im_hoerspiel():
    # Hörspiel-Vorbild: 0,55 zwischen Absätzen, 1,8 nach dem Titel.
    assert vertonung.PAUSE_ZEILE_SEK < 0.55
    assert vertonung.PAUSE_ABSCHNITT_SEK < 1.8


# --------------------------------------------------------------------------
# bauen.py — der ganze Weg
# --------------------------------------------------------------------------

def _langes_skript(zeilen_paare: int = 17) -> str:
    """Ein Skript, das die Längenprobe besteht: ~1200 Wörter, ~8 Minuten."""
    satz_gast = (
        "Der Ort der Verarbeitung ist keine Eigenschaft des Anbieters, "
        "sondern eine Einstellung beim Einrichten, und sie entscheidet, ob "
        "eine Zusage wie die Verarbeitung in Europa überhaupt prüfbar ist, "
        "was man im Vertrag ausdrücklich festhalten muss und der Grund ist, "
        "warum eine Broschüre allein über den Datenweg nichts sagt")
    teile = ["# Wohin die Daten gehen", "",
             "## Worum es geht", "",
             "MODERATOR: Heute geht es darum, wo eine Anfrage gerechnet "
             "wird. [E]",
             "GAST: %s. [B-0043-03]" % satz_gast, ""]
    for i in range(zeilen_paare):
        if i % 10 == 0:
            teile += ["## Abschnitt %d" % (i // 10 + 1), ""]
        teile += [
            "MODERATOR: Und wie prüft man das? [B-0043-02]",
            "GAST: %s. [B-0043-02] [B-0043-04]" % satz_gast,
            "",
        ]
    teile += ["## Zusammenfassung", "",
              "MODERATOR: Halten wir fest. [E]",
              "GAST: %s. [B-0043-05]" % satz_gast, ""]
    return "\n".join(teile)


@pytest.fixture
def skriptdatei(tmp_path):
    pfad = tmp_path / "skript.md"
    pfad.write_text(_langes_skript(), encoding="utf-8")
    return str(pfad)


def test_ganzer_weg_mit_stille(tmp_path, skriptdatei):
    ergebnis = bauen.baue(
        einheiten_pfad=ECHTES_MATERIAL, titel="Wohin die Daten gehen",
        arbeit=str(tmp_path / "arbeit"), skript_datei=skriptdatei)
    assert ergebnis.zustand == "fertig", ergebnis.grund

    assert os.path.exists(ergebnis.audio)
    assert os.path.exists(ergebnis.manifest)
    assert os.path.exists(os.path.join(ergebnis.verzeichnis, "skript.md"))
    assert os.path.exists(os.path.join(ergebnis.verzeichnis, "probe.md"))

    with open(ergebnis.manifest, encoding="utf-8") as f:
        m = json.load(f)
    assert bauen.DAUER_MIN_SEK <= m["dauer_sek"] <= bauen.DAUER_MAX_SEK
    assert m["zeichen_vertont"] > 0                       # POD-7a
    assert m["stimmen"] == {"MODERATOR": "shimmer", "GAST": "onyx"}  # POD-7
    assert m["sprechanteile"]["GAST"] >= bauen.GAST_ANTEIL_MIN       # POD-1a
    assert m["anbieter_vertonung"] == "stille"
    assert [e["id"] for e in m["einheiten"]] == [
        "WE-%04d" % n for n in range(194, 225)]           # AUF-9
    assert all(len(e["stand"]) == 16 for e in m["einheiten"])
    assert m["quellen"] == ["0043"]                     # AUF-12: was das Skript belegt

    # POD-12: Zeitmarken, aufsteigend, erste bei null, mit Art.
    marken = m["kapitelmarken"]
    assert len(marken) >= 3
    assert marken[0]["sek"] == 0
    assert marken[0]["art"] == "einleitung"
    assert marken[-1]["art"] == "zusammenfassung"
    assert [x["sek"] for x in marken] == sorted(x["sek"] for x in marken)
    assert marken[-1]["sek"] < m["dauer_sek"]

    # AUF-6: der Zustand steht auf der Platte, nicht nur im Rückgabewert.
    zustand = bauen.lies_zustand(ergebnis.verzeichnis)
    assert zustand["zustand"] == "fertig"
    assert zustand["zeichen_vertont"] == m["zeichen_vertont"]


def test_gleicher_eingang_gleicher_auftrag_und_cache(tmp_path, skriptdatei):
    arbeit = str(tmp_path / "arbeit")
    erst = bauen.baue(einheiten_pfad=ECHTES_MATERIAL, titel="Gleich",
                      arbeit=arbeit, skript_datei=skriptdatei)
    zweit = bauen.baue(einheiten_pfad=ECHTES_MATERIAL, titel="Gleich",
                       arbeit=arbeit, skript_datei=skriptdatei)
    assert erst.auftrag_id == zweit.auftrag_id          # AUF-7
    assert zweit.zustand == "fertig"

    # POD-7a / E-21b: der zweite Lauf schickt nichts an den Anbieter und
    # kostet deshalb nichts — die Folge selbst ist trotzdem gleich groß.
    # (Im ersten Lauf liegt `neu` unter `vertont`, weil dieses Probe-Skript
    # dieselbe Zeile mehrfach enthält und der Cache schon innerhalb eines
    # Laufs greift.)
    assert 0 < erst.zeichen_neu_vertont <= erst.zeichen_vertont
    assert zweit.zeichen_vertont == erst.zeichen_vertont
    assert zweit.zeichen_neu_vertont == 0

    cache = bauen.TeileCache(os.path.join(arbeit, ".teile"))
    assert cache.index                                   # geerbtes .index.json
    schluessel = bauen.TeileCache.schluessel(
        text="Halten wir fest.", voice="shimmer",
        stimmen=vertonung.STIMMEN, anbieter="stille")
    assert cache.hole(schluessel) is not None


def test_andere_stimmen_geben_anderen_auftrag(tmp_path):
    liste = _einheiten()
    a = bauen.auftrag_id(titel="T", einheiten=liste, stimmen=vertonung.STIMMEN)
    b = bauen.auftrag_id(titel="T", einheiten=liste,
                         stimmen={"MODERATOR": "onyx", "GAST": "shimmer"})
    assert a != b


def test_zu_kurze_folge_scheitert(tmp_path):
    # POD-3: unter fünf Minuten wird mit der nächsten Lektion zusammengelegt.
    pfad = tmp_path / "kurz.md"
    pfad.write_text(GUTES_SKRIPT, encoding="utf-8")
    ergebnis = bauen.baue(
        einheiten_pfad=ECHTES_MATERIAL, titel="Zu kurz",
        arbeit=str(tmp_path / "arbeit"), skript_datei=str(pfad))
    assert ergebnis.zustand == "gescheitert"
    assert "POD-3" in ergebnis.grund
    assert not os.path.exists(ergebnis.audio)            # AUF-7: kein Rest
    assert not os.path.exists(os.path.join(ergebnis.verzeichnis, ".bau"))
    assert bauen.lies_zustand(ergebnis.verzeichnis)["zustand"] == "gescheitert"


def test_erfundene_passage_laesst_den_auftrag_scheitern(tmp_path):
    pfad = tmp_path / "erfunden.md"
    pfad.write_text(
        _langes_skript().replace(
            "MODERATOR: Und wie prüft man das? [B-0043-02]",
            "MODERATOR: Und wie ist das bei Bildmodellen?", 1),
        encoding="utf-8")
    ergebnis = bauen.baue(
        einheiten_pfad=ECHTES_MATERIAL, titel="Erfunden",
        arbeit=str(tmp_path / "arbeit"), skript_datei=str(pfad))
    assert ergebnis.zustand == "gescheitert"
    assert "Belegprobe" in ergebnis.grund
    assert not os.path.exists(ergebnis.audio)
    with open(os.path.join(ergebnis.verzeichnis, "probe.md"),
              encoding="utf-8") as f:
        assert "GESCHEITERT" in f.read()


def test_aufgeteilter_vortrag_scheitert(tmp_path):
    # POD-1a: der Moderator erklärt hier genauso viel wie der Gast.
    lang = _langes_skript().replace("MODERATOR: Und wie prüft man das?",
                                    "MODERATOR: " + "x " * 120 + "und?")
    pfad = tmp_path / "vortrag.md"
    pfad.write_text(lang, encoding="utf-8")
    ergebnis = bauen.baue(
        einheiten_pfad=ECHTES_MATERIAL, titel="Vortrag",
        arbeit=str(tmp_path / "arbeit"), skript_datei=str(pfad))
    assert ergebnis.zustand == "gescheitert"
    assert "POD-1a" in ergebnis.grund


def test_proben_schreiben_nicht_nach_tmp(tmp_path):
    """APP-11: Diese Proben erzeugen MP3s und gehören nicht ins System-Temp.

    Geprüft wird die **Anforderung** (nicht im System-Temp), nicht ein
    bestimmtes Verzeichnis. Sonst scheitert der Test, sobald er zusammen mit
    einer Nachbar-Suite läuft, die ihr Basisverzeichnis anders setzt —
    `dienst/tests/conftest.py` tut genau das über `config.option.basetemp`.
    Beide Wege erfüllen APP-11; die Anforderung ist dieselbe.
    """
    assert not str(tmp_path).startswith("/tmp/")
    assert not str(tmp_path).startswith("/var/tmp/")
    assert "/arbeit/" in str(tmp_path), (
        "Proben gehören unter ein arbeit/-Verzeichnis im Repo, "
        "damit sie im .gitignore stehen und nicht im System-Temp landen.")


def test_tempoaenderung_bricht_den_cache():
    """Sonst wirkt eine Tempoänderung nicht (Fehler vom 11.09.2026).

    Das Hörspiel-Vorbild warnt an derselben Stelle vor demselben Fehler für die
    Voice-Map. Hier ist er für das Sprechtempo einmal wirklich passiert: Der
    Lauf meldete „39 aus dem Cache, 0 neu" und die Folge klang unverändert.
    """
    args = dict(text="Probe", voice="onyx",
                stimmen={"MODERATOR": "shimmer", "GAST": "onyx"}, anbieter="azure")
    alt = bauen.TeileCache.schluessel(**args)
    import podcast.vertonung as v
    frueher = v.SPRECHTEMPO
    try:
        v.SPRECHTEMPO = frueher + 0.2
        assert bauen.TeileCache.schluessel(**args) != alt
    finally:
        v.SPRECHTEMPO = frueher


# --- POD-18: die vierte Wand ----------------------------------------------
#
# Der Anlass ist ein gehörter Fehler, nicht eine gedachte Möglichkeit: In
# einer fertigen Folge sagte der Moderator, er habe keine Beispiele in den
# Daten (13.09.2026). Achtzehn von siebenundvierzig Folgen trugen dazu eine
# eigene gesprochene Überschrift.

VIERTE_WAND_SKRIPT = """# Ein Titel

## Eröffnung

MODERATOR: Heute geht es um den gemeinsamen Kanal. [E]
GAST: Anweisung und Daten laufen durch denselben Eingang. [B-0043-03]

## Wenn das Material nicht trägt

MODERATOR: Der Auftrag verlangt einen benannten Fall. Trägt das Material? [E]
GAST: In der übergebenen Materialbasis steht keiner. [E]

## Zusammenfassung

MODERATOR: Bleibt: ein Kanal, zwei Bedeutungen. [E]
"""


def test_werkstatt_gespraech_wird_gefangen():
    s = skript.lies(VIERTE_WAND_SKRIPT)
    befunde = belegprobe.pruefe_vierte_wand(s)
    arten = {b.art for b in befunde}
    assert "werkstatt-als-kapitel" in arten, "die Kapitelmarke ist der sichtbarste Ort"
    assert "werkstatt-im-audio" in arten
    # Die Eröffnung und die Zusammenfassung reden über die Sache, nicht über uns.
    assert not any("Zeile 5" in b.ort or "Zeile 6" in b.ort for b in befunde)


def test_werkstatt_probe_blockiert_den_bau():
    # Sie hängt in `pruefe`, also scheitert der Bau, nicht nur ein Bericht.
    s = skript.lies(VIERTE_WAND_SKRIPT)
    probe = belegprobe.pruefe(s, [])
    assert not probe.bestanden
    assert any(b.art.startswith("werkstatt") for b in probe.befunde)


def test_ehrlichkeit_ueber_die_sache_bleibt_erlaubt():
    """POD-18 trennt nach dem Gegenstand des Satzes, nicht nach dem Thema.

    „Dazu gibt es kaum Zahlen" redet über den Forschungsstand und gehört
    hinein (POD-5, und der Auftrag verlangt es sogar). „Das steht nicht in
    unserem Material" redet über uns.
    """
    erlaubt = [
        "Dazu gibt es bisher kaum belastbare Zahlen.",
        "Die Studienlage ist an dieser Stelle dünn.",
        "Das weiß ich nicht.",
        "Heute geht es um Auftragsverarbeitung in der Praxis.",
        "Der Agent hat den Auftrag, Rechnungen zu lesen.",
        "Die Daten werden im Auftrag des Nutzers verarbeitet.",
    ]
    for satz in erlaubt:
        assert not belegprobe.WERKSTATT_RE.search(satz), satz


# --- AUF-18a: die Fassung der Pipeline ------------------------------------

def test_fassung_passt_zum_auftragstext():
    """Die Probe, die verhindert, dass die Fassungsnummer luegt.

    Die Zahl wird von Hand gepflegt (kein Build-Schritt, E-5). Aendert sich
    `auftrag.md`, ohne dass jemand die Fassung erhoeht, behauptet jede neue
    Folge etwas Falsches ueber sich. Deshalb haelt das Register den Stand des
    Auftragstexts fest, bei dem die Fassung festgelegt wurde.

    Faellt dieser Test: entweder `STAND_BEI_FESTLEGUNG` nachziehen (kleine
    Aenderung) oder eine neue Fassung anlegen (neue Regel).
    """
    from podcast import fassung
    assert fassung.pruefe_stand() is None, fassung.pruefe_stand()


def test_fassungen_sind_absteigend_und_lueckenlos():
    from podcast import fassung
    nummern = [f.nummer for f in fassung.FASSUNGEN]
    assert nummern == sorted(nummern, reverse=True), "neueste zuerst"
    assert nummern == list(range(max(nummern), 0, -1)), "keine Luecke"
    assert fassung.JETZIGE.nummer == max(nummern)
    for f in fassung.FASSUNGEN:
        assert f.was, f"Fassung {f.nummer} sagt nicht, was sie besser macht"
        assert f.regeln, f"Fassung {f.nummer} nennt keine Regel"


def test_fracht_traegt_klartext_und_stand():
    from podcast import fassung
    fracht = fassung.als_fracht()
    assert fracht["nummer"] == fassung.JETZIGE.nummer
    assert fracht["auftrag_stand"] == fassung.stand_des_auftrags()
    # Der Mensch liest das in der App — eine Nummer allein sagt ihm nichts.
    assert any("Fachbegriff" in w for w in fracht["was"])


def test_eine_alte_fassung_bleibt_abfragbar():
    # POD-16a: Fertige Folgen werden nicht neu gebaut. Also muss der Klartext
    # zu einer alten Fassung erhalten bleiben, sonst steht an der Folge eine
    # Zahl ohne Bedeutung.
    from podcast import fassung
    alt = fassung.als_fracht(1)
    assert alt["nummer"] == 1
    assert alt["was"], "Fassung 1 muss lesbar bleiben"
