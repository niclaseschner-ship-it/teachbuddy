"""Der Flask-Dienst gegen Datenvertrag v2 und das echte Material."""

from __future__ import annotations

import json

from dienst.folie import folie_punkte


# -- Lesen ------------------------------------------------------------------


def test_lernpfad_liefert_die_kapitel_aus_der_bibliothek(klient):
    a = klient.get("/api/lernpfad/P-02")
    assert a.status_code == 200
    d = a.get_json()
    assert d["lernpfad"]["id"] == "P-02"
    assert d["lernpfad"]["titel"]
    assert d["lernpfad"]["kapitel_gesamt"] == len(d["kapitel"])
    assert "lektionen_gesamt" not in d["lernpfad"], "R-1/R-2: keine Aggregate im Vertrag"
    assert "fortschritt" not in d["lernpfad"], "R-1/R-2: Fortschritt wird abgeleitet"
    nummern = [k["nummer"] for k in d["kapitel"]]
    assert nummern == sorted(nummern)
    for k in d["kapitel"]:
        assert k["id"] and k["titel"]
        assert isinstance(k["lektionen"], list)


def test_lernpfad_sagt_was_fehlt_statt_leer_zu_sein(klient):
    """Leere Listen brauchen eine Begruendung — gefuellte nicht.

    Hat ein Kapitel keine Lektionen, muss der Dienst sagen warum.
    """
    d = klient.get("/api/lernpfad/P-02").get_json()
    mit = [k for k in d["kapitel"] if k["lektionen"]]
    ohne = [k for k in d["kapitel"] if not k["lektionen"]]
    assert mit, "das Demo-Kapitel hat Lektionen"
    if ohne:
        assert "_fehlt" in d, "eine leere Lektionsliste ohne Begruendung ist eine Luege"


def test_unbekannter_lernpfad(klient):
    a = klient.get("/api/lernpfad/P-99")
    assert a.status_code == 404
    assert a.get_json()["fehler"] == "lernpfad_unbekannt"


def test_lektion_gibt_es_noch_nicht_und_sagt_warum(klient):
    a = klient.get("/api/lektion/L-023")
    assert a.status_code == 404
    d = a.get_json()
    assert d["fehler"] == "lektion_unbekannt"
    assert "BIB-26" in d["offen"]


def test_kapitel_mindmap(klient):
    a = klient.get("/api/kapitel/K-03/mindmap")
    assert a.status_code == 200
    d = a.get_json()
    assert d["kapitel_id"] == "K-03"
    assert d["wurzel"]["art"] == "wurzel"
    assert d["wurzel"]["label"]
    assert isinstance(d["belege"], dict)
    if not d.get("wurzel", {}).get("kinder"):
        assert "_fehlt" in d, "ohne Knoten muss die Luecke benannt sein"


def test_unbekanntes_kapitel(klient):
    assert klient.get("/api/kapitel/Z/mindmap").status_code == 404


def test_beleg_kommt_vollstaendig(klient):
    """R-5-Gegenstueck: der Einzelabruf fuer Belege aus einem Gespraech."""
    a = klient.get("/api/beleg/B-0043-03")
    assert a.status_code == 200
    d = a.get_json()
    assert d["aussage"] and d["zitat"] and d["stelle"]
    assert d["quelle"]["id"] == "Q-0043"
    assert d["zuversicht"]
    assert klient.get("/api/beleg/B-9999-99").status_code == 404


# -- R-5: Belege reisen ausgeschrieben mit ----------------------------------


def test_r5_belege_sind_ausgeschrieben_nicht_nachzuladen(db, klient):
    """Der wichtigste Punkt des Auftrags, gegen das echte Material geprueft.

    Es gibt heute keine Lektion, an der sich das im Endpunkt zeigen liesze.
    Geprueft wird deshalb der Mechanismus selbst: Aus einer Wissenseinheit
    werden Folienpunkte mit Belegverweisen, und zu jedem Verweis liegt der
    ausgeschriebene Beleg in derselben Antwort.
    """
    from bibliothek import abfragen

    einheit = abfragen.einheit(db, "WE-0217")
    punkte = folie_punkte(einheit["inhalt"])
    verweise = {b for p in punkte for b in p["belege"]}
    assert verweise, "die Einheit traegt keine Belegverweise"

    ausgeschrieben = abfragen.belege_ausgeschrieben(db, sorted(verweise))
    assert set(ausgeschrieben) == verweise
    for bid, beleg in ausgeschrieben.items():
        assert not beleg.get("fehlt"), bid
        assert beleg["aussage"].strip(), bid
        assert beleg["zitat"].strip(), bid
        assert beleg["stelle"].strip(), bid
        assert beleg["quelle_id"], bid
        assert beleg["zuversicht"], bid
    # Im Zug ist der Server nicht erreichbar: Nach dem Laden darf nichts fehlen.
    fracht = json.dumps({"folie_punkte": punkte, "belege": ausgeschrieben})
    for bid in verweise:
        assert bid in fracht


def test_folie_punkte_lesen_die_markierung_ab(db):
    """R-6/BIB-11: belegt gegen einordnung, abgelesen statt geraten."""
    from bibliothek import abfragen

    einheit = abfragen.einheit(db, "WE-0194")
    punkte = folie_punkte(einheit["inhalt"])
    arten = {p["art"] for p in punkte}
    assert "belegt" in arten
    assert "einordnung" in arten
    assert "unbelegt" not in arten, "unbelegte Aussage im Material (BIB-11)"
    for p in punkte:
        assert "[B-" not in p["text"], "Belegmarke steht noch im Text"
        assert "[E]" not in p["text"]
        if p["art"] == "belegt":
            assert p["belege"]
        assert "strittig" not in arten, "strittig wird nicht geraten"


def test_folie_punkte_aller_einheiten_sind_belegt_oder_einordnung(db):
    from bibliothek import abfragen

    # **Dieser Test hat eine Absicht behauptet, nicht den Stand.** Bis zum
    # 13.09.2026 stand hier `assert not unbelegt` — und die Bibliothek hatte
    # 270 unmarkierte Absaetze. Der Test war rot und wurde als fremde
    # Baustelle gelesen, statt als Befund.
    #
    # Was jetzt geprueft wird, ist das, was wirklich gelten muss: Jeder
    # Absatz wird zu einem Punkt, jeder Punkt traegt eine bekannte Art, und
    # **kein unmarkierter Absatz verschwindet stillschweigend** — er steht als
    # Befund `absatz_ohne_marker` im Index (BIB-11) und wird in der App als
    # ungekennzeichnet gezeichnet (OBF-17).
    arten = {"belegt", "einordnung", "unbelegt", "strittig"}
    ohne_marker = set()
    for r in db.execute("SELECT id FROM einheiten"):
        einheit = abfragen.einheit(db, r["id"])
        punkte = folie_punkte(einheit["inhalt"])
        assert punkte, r["id"]
        for p in punkte:
            assert p["art"] in arten, (r["id"], p["art"])
            if p["art"] == "belegt":
                assert p["belege"], (r["id"], "belegt ohne Beleg")
        if any(p["art"] == "unbelegt" for p in punkte):
            ohne_marker.add(r["id"])

    gemeldet = {f["betrifft"] for f in abfragen.befunde(db)
                if f["art"] == "absatz_ohne_marker"}
    assert ohne_marker <= gemeldet, (
        "unmarkierte Absaetze, die kein Befund nennt: %s"
        % sorted(ohne_marker - gemeldet)[:5])


# -- Schreiben (OBF-7) -------------------------------------------------------


def test_fortschritt_schreiben_und_lesen(klient, lernstand):
    a = klient.put("/api/lektion/L-007/fortschritt", json={"position_sek": 138, "fragen": "offen"})
    assert a.status_code == 200
    assert a.get_json()["ok"] is True


def test_fortschritt_weist_unsinn_zurueck(klient):
    assert klient.put("/api/lektion/L-007/fortschritt", json={}).status_code == 400
    assert (
        klient.put(
            "/api/lektion/L-007/fortschritt", json={"position_sek": 10, "fragen": "halb"}
        ).status_code
        == 400
    )


def test_nachtrag_spaeterer_zeitpunkt_gewinnt(klient):
    """R-3/APP-7: Der Server entscheidet, nicht der Browser."""
    frueh = {
        "lektion_id": "L-007",
        "position_sek": 100,
        "fragen": "offen",
        "zeitpunkt": "2026-09-11T08:00:00+02:00",
    }
    spaet = {**frueh, "position_sek": 200, "zeitpunkt": "2026-09-11T09:00:00+02:00"}

    a = klient.post("/api/fortschritt/nachtrag", json=[spaet])
    assert a.get_json()["uebernommen"] == 1

    b = klient.post("/api/fortschritt/nachtrag", json=[frueh])
    d = b.get_json()
    assert d["uebernommen"] == 0
    assert d["verworfen"][0]["lektion_id"] == "L-007"
    assert "spaeterer" in d["verworfen"][0]["grund"]


def test_nachtrag_reihenfolge_in_der_liste_ist_egal(lernstand):
    frueh = {
        "lektion_id": "L-009",
        "position_sek": 10,
        "fragen": "offen",
        "zeitpunkt": "2026-09-11T08:00:00+02:00",
    }
    spaet = {**frueh, "position_sek": 99, "zeitpunkt": "2026-09-11T10:00:00+02:00"}
    lernstand.nachtrag([spaet, frueh])
    assert lernstand.fortschritt("L-009")["position_sek"] == 99
    lernstand2 = type(lernstand)(lernstand.pfad.parent / "zweiter.db")
    lernstand2.nachtrag([frueh, spaet])
    assert lernstand2.fortschritt("L-009")["position_sek"] == 99


def test_nachtrag_verwirft_unvollstaendige_saetze(klient):
    d = klient.post("/api/fortschritt/nachtrag", json=[{"position_sek": 1}]).get_json()
    assert d["uebernommen"] == 0
    assert d["verworfen"][0]["grund"]


def test_nachtrag_braucht_eine_liste(klient):
    assert klient.post("/api/fortschritt/nachtrag", json={"a": 1}).status_code == 400


def test_einstellungen_tempo(klient):
    a = klient.put("/api/einstellungen", json={"tempo": 1.5})
    assert a.status_code == 200
    assert a.get_json()["tempo"] == 1.5
    assert klient.put("/api/einstellungen", json={"tempo": 99}).status_code == 400
    assert klient.put("/api/einstellungen", json={}).status_code == 400


# -- Antwortbewertung: ehrliche Enthaltung (PRF-9) --------------------------


def test_antwort_ist_nicht_bewertbar_und_sagt_warum(klient):
    a = klient.post("/api/frage/WE-0194/antwort", json={"text": "Weil der Bereitstellungstyp entscheidet."})
    assert a.status_code == 200
    d = a.get_json()
    assert d["bewertung"] == "nicht_bewertbar"
    assert "Modell" in d["begruendung"]
    assert d["getroffen"] == [] and d["gefehlt"] == []
    assert d["gespeichert"] is True
    assert d["prueffrage"], "die Prueffrage der Einheit liegt im Material vor"
    assert d["belege"], "die Belege der Einheit gehoeren zur Antwort"
    assert set(d["belege_ausgeschrieben"]) == set(d["belege"])
    assert "_offen" in d


def test_antwort_auf_unbekannte_frage_geht_nicht_verloren(klient):
    d = klient.post("/api/frage/F-023-1/antwort", json={"text": "irgendwas"}).get_json()
    assert d["bewertung"] == "nicht_bewertbar"
    assert d["gespeichert"] is True
    assert "_frage_unbekannt" in d


def test_antwort_ohne_text(klient):
    assert klient.post("/api/frage/WE-0194/antwort", json={"text": "  "}).status_code == 400


def test_antwort_wird_gespeichert(index_pfad, tmp_path):
    from dienst.app import erzeuge_app
    from dienst.lernstand import Lernstand

    lernstand_pfad = tmp_path / "lernstand.db"
    app = erzeuge_app(index_pfad, lernstand_pfad)
    app.test_client().post("/api/frage/WE-0194/antwort", json={"text": "meine Antwort"})
    gemerkt = Lernstand(lernstand_pfad).antworten("WE-0194")
    assert [a["text"] for a in gemerkt] == ["meine Antwort"]
    assert gemerkt[0]["bewertung"] == "nicht_bewertbar"


# -- Betrieb ----------------------------------------------------------------


def test_zustand_meldet_index_und_befunde(klient):
    d = klient.get("/api/zustand").get_json()
    assert d["index"]["gebaut_am"]
    assert int(d["index"]["belege"]) > 30
    assert d["befunde"]["abweichung"] > 0
    assert d["fehler"] == []
    assert d["lernstand"]["tempo"] == 1.0


def test_nebenlaeufige_zugriffe(index_pfad, tmp_path):
    """Eine SQLite-Verbindung gehoert einem Strang.

    Der Entwicklungsserver bedient nebenlaeufig; eine geteilte Verbindung
    faellt hier mit 'created in a thread' um.
    """
    import threading

    from dienst.app import erzeuge_app

    app = erzeuge_app(index_pfad, tmp_path / "lernstand.db")
    ergebnisse: list[int] = []
    fehler: list[BaseException] = []

    def laufe():
        try:
            with app.test_client() as c:
                for weg in ("/api/lernpfad/P-02", "/api/beleg/B-0043-03", "/api/zustand"):
                    ergebnisse.append(c.get(weg).status_code)
        except BaseException as f:  # noqa: BLE001
            fehler.append(f)

    straenge = [threading.Thread(target=laufe) for _ in range(6)]
    for s in straenge:
        s.start()
    for s in straenge:
        s.join()

    assert not fehler, fehler
    assert ergebnisse == [200] * 18


def test_unbekannter_weg(klient):
    a = klient.get("/api/gibtsnicht")
    assert a.status_code == 404
    assert a.get_json()["fehler"] == "unbekannter_weg"


# -- AUF-18a und OBF-19: Fassung und Rueckmeldung ----------------------------


def test_lektion_nennt_ihre_pipeline_fassung(klient):
    """AUF-18a — an der Folge steht, womit sie gebaut wurde."""
    a = klient.get("/api/lektion/L-H1")
    assert a.status_code == 200
    p = a.get_json()["pipeline"]
    assert p["nummer"] == 3
    assert p["erzeugt"] == "2026-10-06"
    assert p["aktuell"] is True
    # Klartext, nicht nur eine Zahl — der Mensch liest das in der App.
    assert any("Fachbegriff" in w for w in p["was"])
    assert "POD-18" in p["regeln"]


def test_alte_folge_sagt_dass_sie_vor_der_zaehlung_entstand(wissen, tmp_path):
    """TB-8: sagen, was man nicht weiss, statt eine Eins zu erfinden.

    Alle Demo-Folgen tragen ihre Fassung. Eine Folge von vor der Zaehlung
    entsteht hier, indem eine Kopie der Bibliothek das Feld verliert.
    """
    import re
    import shutil
    from bibliothek.index import baue_index
    from dienst.app import erzeuge_app
    kopie = tmp_path / "wissen"
    shutil.copytree(wissen, kopie, ignore=shutil.ignore_patterns("audio", "bilder"))
    lektion = kopie / "eingang" / "M-016" / "lektionen" / "L-H1.md"
    lektion.write_text(re.sub(r"^pipeline:.*\n", "", lektion.read_text(), flags=re.M))
    baue_index(kopie, tmp_path / "index.db")
    klient = erzeuge_app(tmp_path / "index.db", tmp_path / "lernstand.db").test_client()
    p = klient.get("/api/lektion/L-H1").get_json()["pipeline"]
    assert p["nummer"] is None
    assert p["hinweis"]
    assert p["jetzige"] == 3


def test_bewertung_der_folge_schreibt_die_fassung_mit(klient):
    """OBF-19 — und zwar auf dem Server, nicht aus dem Browser.

    Eine Bewertung gilt fuer den Stand, der gehoert wurde. Wer sie spaeter
    gegen die dann aktuelle Fassung liest, deutet sie falsch.

    Bewertet wird die **Folge**: Der Browser schickt keine Einheit mit.
    """
    a = klient.post("/api/lektion/L-H1/rueckmeldung",
                    json={"art": "gut", "text": "Klingt wesentlich besser."})
    assert a.status_code == 200
    assert a.get_json()["gemerkt"] is True

    alle = klient.get("/api/rueckmeldungen?lektion=L-H1").get_json()["rueckmeldungen"]
    assert len(alle) == 1
    r = alle[0]
    assert r["einheit_id"] is None, "die Bewertung gilt der Folge"
    assert r["art"] == "gut"
    # Das ist der Punkt des Ganzen:
    assert r["pipeline"] == 3
    assert r["erzeugt"] == "2026-10-06"


def test_eine_einzelne_stelle_bleibt_moeglich(klient):
    """Der Datenweg traegt weiter eine Einheit, die Oberflaeche fragt nicht.

    OBF-19 hat das Symbol je Einheit verworfen („ich will den podcast bewerten
    und nicht 100.000 text stellen"). Der Vertrag bleibt offen, damit eine
    einzelne Stelle benannt werden *kann*, ohne dass jeder Absatz einen Knopf
    braucht.
    """
    a = klient.post("/api/lektion/L-H1/rueckmeldung",
                    json={"art": "unklar", "einheit": "WE-0194",
                          "text": "Der Unterschied Global/DataZone ging mir zu schnell."})
    assert a.status_code == 200
    alle = klient.get("/api/rueckmeldungen?lektion=L-H1").get_json()["rueckmeldungen"]
    assert alle[0]["einheit_id"] == "WE-0194"


def test_rueckmeldung_ohne_art_und_ohne_text_wird_abgewiesen(klient):
    assert klient.post("/api/lektion/L-H1/rueckmeldung",
                       json={"art": "quatsch"}).status_code == 400
    # „anderes" ohne Satz sagt nichts.
    assert klient.post("/api/lektion/L-H1/rueckmeldung",
                       json={"art": "sonst"}).status_code == 400
    # Eine Art allein genuegt dagegen — ein Daumen ist eine Aussage.
    assert klient.post("/api/lektion/L-H1/rueckmeldung",
                       json={"art": "gut"}).status_code == 200


def test_rueckmeldung_zu_unbekannter_lektion(klient):
    a = klient.post("/api/lektion/L-GIBTSNICHT/rueckmeldung", json={"art": "gut"})
    assert a.status_code == 404


# -- DIS-24..29: die vier Werkzeuge des Gespraechspartners --------------------


def test_die_sitzung_gibt_dem_partner_vier_werkzeuge():
    """DIS-25 — sie waren seit dem 11.09.2026 vereinbart und nie gebaut.

    Geprueft wird das Modul, nicht der Anbieteraufruf: Eine Sitzung anzulegen
    kostet Geld und braucht Netz.
    """
    from dienst import werkzeuge
    namen = {w["name"] for w in werkzeuge.ERKLAERUNGEN}
    assert namen == {"bibliothek_nachschlagen", "recherchieren",
                     "rechercheauftrag_aufnehmen", "punkt_geprueft"}
    for w in werkzeuge.ERKLAERUNGEN:
        assert w["type"] == "function"
        assert w["parameters"]["required"], w["name"]
        # DIS-27: Der Partner soll aus der Beschreibung das Tempo kennen.
        assert w["description"], w["name"]


def test_nachschlagen_geht_ueber_das_kapitel_hinaus(db):
    """DIS-26 — genau dafuer wurde der Volltextindex gebaut."""
    from dienst import werkzeuge
    fund = werkzeuge.nachschlagen(db, "Subunternehmer Widerspruch")
    assert fund["herkunft"] == "bibliothek"
    assert fund["treffer"]
    kapitel = {t["kapitel"] for t in fund["treffer"]}
    assert len(kapitel) >= 1
    # Was hier zurueckkommt, ist belegt — sonst waere die Zusage falsch.
    assert any(t["belege"] for t in fund["treffer"])


def test_nachschlagen_haelt_rohe_eingabe_aus(db):
    """fts5 wirft bei einem Apostroph oder einem `OR` einen Syntaxfehler.

    Die Frage kommt woertlich aus einem gesprochenen Satz. Ein Werkzeug, das
    daran scheitert, laesst den Partner mitten im Gespraech raten.
    """
    from dienst import werkzeuge
    for frage in ("Was heisst \"Top-K\" OR Top-P?", "Agent's Trajektorie -- wieso?",
                  "???", "", "a b"):
        fund = werkzeuge.nachschlagen(db, frage)
        assert "treffer" in fund


def test_werkzeug_nachschlagen_ueber_den_verteiler(klient):
    a = klient.post("/api/sitzung/S-test/werkzeug", json={
        "werkzeug": "bibliothek_nachschlagen",
        "argumente": {"frage": "Wechselfrist Data Act"}})
    assert a.status_code == 200
    assert a.get_json()["herkunft"] == "bibliothek"


def test_rechercheauftrag_landet_im_rueckkanal(klient):
    """OBF-18/DIS-9 — die Luecken zeigt der Lernende, nicht der Kurator."""
    a = klient.post("/api/sitzung/S-test/werkzeug", json={
        "werkzeug": "rechercheauftrag_aufnehmen", "kapitel": "K-03",
        "argumente": {"frage": "Was kostet ein Wechsel zurück ins eigene Rechenzentrum?",
                      "zusammenhang": "nach der Wechselfrist"}})
    assert a.get_json() == {"aufgenommen": True}

    alle = klient.get("/api/recherchen?auftraege=1").get_json()["recherchen"]
    assert len(alle) == 1
    assert alle[0]["frage"] == "Was kostet ein Wechsel zurück ins eigene Rechenzentrum?"
    assert alle[0]["auftrag"] == 1
    # Ein Auftrag ist keine Antwort.
    assert alle[0]["antwort"] is None


def test_agenda_wird_abgehakt_und_ist_ueberschreibbar(klient, lernstand):
    a = klient.post("/api/sitzung/S-test/werkzeug", json={
        "werkzeug": "punkt_geprueft",
        "argumente": {"id": "AG-WE-0194", "urteil": "halb", "begruendung": "nur halb"}})
    assert a.get_json()["urteil"] == "halb"
    # Ein zweiter Durchgang im selben Gespraech darf das Urteil aendern.
    b = klient.post("/api/sitzung/S-test/werkzeug", json={
        "werkzeug": "punkt_geprueft",
        "argumente": {"id": "AG-WE-0194", "urteil": "sitzt"}})
    assert b.get_json()["urteil"] == "sitzt"


def test_ein_unbekanntes_werkzeug_bricht_nichts_ab(klient):
    """TB-8: Der Partner soll sagen koennen, dass es nicht ging.

    Ein 500er laesst ihn mitten im Satz auf etwas warten, das nie kommt.
    """
    a = klient.post("/api/sitzung/S-test/werkzeug", json={"werkzeug": "zaubern"})
    assert a.status_code == 200
    assert a.get_json()["fehler"] == "werkzeug_unbekannt"

    b = klient.post("/api/sitzung/S-test/werkzeug", json={
        "werkzeug": "punkt_geprueft", "argumente": {"id": "AG-1", "urteil": "quatsch"}})
    assert b.status_code == 200
    assert b.get_json()["fehler"] == "urteil_unbekannt"


def test_werkzeuge_nur_wenn_der_browser_sie_ausfuehren_kann(klient, monkeypatch):
    """Der Handschlag, der am 14.09.2026 gefehlt hat.

    Der Server war neu und lieferte dem Partner vier Werkzeuge; im Browser lag
    noch die alte `gespraech.js` aus dem Service-Worker-Mantel. Der Partner
    rief ein Werkzeug, niemand antwortete, er wartete — und nach fuenfzehn
    Sekunden Stille schloss die Sitzung. Aus die Sicht: "kaputt, er schliesst
    einfach und antwortet auch nicht."

    Ein Neuladen haette es behoben und waere die falsche Antwort: Der Service
    Worker laesst einen neuen Mantel absichtlich warten, bis keine alte Seite
    mehr offen ist. Also darf die Sitzung nicht davon abhaengen, welche
    Fassung gerade im Browser liegt.
    """
    import json as _json
    import urllib.request

    import zugang

    gesehen = {}

    class _Antwort:
        def read(self):
            return b'{"value": "tok", "session": {"model": "gpt-realtime"}}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    def _fake(anfrage, timeout=None):
        gesehen["rumpf"] = _json.loads(anfrage.data)
        return _Antwort()

    monkeypatch.setattr(urllib.request, "urlopen", _fake)
    monkeypatch.setattr(zugang, "hole", lambda *a, **k: "sk-probe")

    # Alter Browser: schickt das Feld nicht.
    klient.post("/api/kapitel/K-03/sprachsitzung", json={})
    sitzung = gesehen["rumpf"]["session"]
    assert sitzung["tools"] == [], "ohne Handschlag keine Werkzeuge"
    assert sitzung["tool_choice"] == "none"
    # Und die Anweisung verspricht dann auch keine.
    assert "bibliothek_nachschlagen" not in sitzung["instructions"]

    # Neuer Browser: sagt, was er kann.
    klient.post("/api/kapitel/K-03/sprachsitzung", json={"werkzeuge": True})
    sitzung = gesehen["rumpf"]["session"]
    assert len(sitzung["tools"]) == 4
    assert sitzung["tool_choice"] == "auto"
    assert "bibliothek_nachschlagen" in sitzung["instructions"]


def test_die_pausenerkennung_steht_und_antwortet_von_allein(klient, monkeypatch):
    """Wer `turn_detection` selbst setzt, erbt die Voreinstellungen nicht.

    Ohne `create_response` antwortet der Partner gar nicht mehr von allein —
    derselbe Befund aus die Sicht wie beim fehlenden Handschlag.
    """
    import json as _json
    import urllib.request

    import zugang

    gesehen = {}

    class _Antwort:
        def read(self):
            return b'{"value": "tok", "session": {"model": "gpt-realtime"}}'
        def __enter__(self): return self
        def __exit__(self, *a): return False

    monkeypatch.setattr(urllib.request, "urlopen",
                        lambda a, timeout=None: (gesehen.update(r=_json.loads(a.data)), _Antwort())[1])
    monkeypatch.setattr(zugang, "hole", lambda *a, **k: "sk-probe")

    klient.post("/api/kapitel/K-03/sprachsitzung", json={"werkzeuge": True})
    vad = gesehen["r"]["session"]["audio"]["input"]["turn_detection"]
    assert vad["silence_duration_ms"] >= 900, "wer denkt, braucht laengere Pausen"
    assert vad["create_response"] is True
    assert vad["interrupt_response"] is True
