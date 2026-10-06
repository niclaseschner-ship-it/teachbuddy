"""Der Flask-Dienst nach Datenvertrag v2.

Zwei Datenquellen, streng getrennt:

* ``index.db``      — gebaut aus der Bibliothek, wegwerfbar, nur lesend (BIB-18b)
* ``lernstand.db``  — eigene Wahrheit, wird geschrieben (OBF-7)

Der wichtigste Punkt ist **R-5**: Belege kommen ausgeschrieben mit, nicht als
nachzuladende IDs. Im Zug ist der Server nicht erreichbar, und ein fehlender Beleg
ist genau der Zustand, den TB-1 ausschlieszt.

Der zweite wichtige Punkt ist, was der Dienst **nicht** tut: Wo das Material
eine Schicht nicht hat, liefert er keine erfundene. Solche Stellen tragen ein
``_fehlt`` mit Begruendung, statt leer oder plausibel auszusehen.

Starten::

    python -m bibliothek.index                 # Index bauen
    FLASK_APP=dienst.app flask run             # oder: python -m dienst.app
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request

import pfade
from bibliothek import abfragen
from bibliothek.index import IndexJeStrang

from .folie import folie_punkte
from . import werkzeuge as werkzeuge_mod

# AUF-18a: Das Fassungsregister der Podcast-Pipeline. Reine Daten, keine
# Abhaengigkeit in die andere Richtung — der Dienst braucht den Klartext zu
# einer Nummer, und die Nummer allein sagt dem Menschen nichts.
from podcast import fassung as fassung_mod
from .kosten import Kosten
from .lernstand import FRAGEN_ZUSTAENDE, Lernstand

__all__ = ["erzeuge_app"]

GEHOERT_SCHWELLE = 0.95  # R-4: Outros werden uebersprungen
TEMPO_GRENZEN = (0.5, 3.0)

LEKTIONSSCHICHT_FEHLT = (
    "Die Bibliothek hat keine Lektionsschicht. BIB-26/27 sehen sie vor, im "
    "Material (der Bibliothek) gibt es aber weder Lektionsdateien noch ein "
    "Feld, das eine Wissenseinheit einem Abschnitt zuordnet — die Zuordnung "
    "steht heute nur in Prosa (eingang/M-001/AUFTRAG.md: 'Abschnitt F'). Sie "
    "wird nicht aus Prosa geraten (CONTRIBUTING.md, Regel 2). Sobald es "
    "Lektionsdateien gibt, fuellen sich diese Felder ohne Codeaenderung."
)

BEWERTUNG_FEHLT = (
    "Die Bewertung braucht ein Modell (PRF-7: Begruendung am Beleg). Das "
    "Denken laeuft ueber die Abo-CLIs (TB-5) und ist an diesen Dienst noch "
    "nicht angeschlossen. PRF-9 verlangt in diesem Fall die Enthaltung: Eine "
    "falsch als richtig bewertete Antwort ist der teuerste Fehler des Formats, "
    "weil der Lernende das Thema abhakt. Die Antwort ist gespeichert und kann "
    "nachtraeglich bewertet werden."
)


# --------------------------------------------------------------------------
# Anwendung
# --------------------------------------------------------------------------


def erzeuge_app(index_pfad: str | Path | None = None, lernstand_pfad: str | Path | None = None) -> Flask:
    app = Flask(__name__)
    # Ohne das schluckt Flask jede info-Zeile, und das Journal zeigt nur
    # Zugriffe. Was der Browser kann, gehoert aber hinein (14.09.2026).
    app.logger.setLevel(logging.INFO)
    app.json.ensure_ascii = False
    app.json.sort_keys = False

    index_pfad = Path(index_pfad or pfade.INDEX)
    lernstand_pfad = Path(
        lernstand_pfad
        or os.environ.get("TEACHBUDDY_LERNSTAND")
        or pfade.ARBEIT / "lernstand.db"
    )
    # Je Strang eine eigene Index-Verbindung: Der Entwicklungsserver bedient
    # nebenlaeufig, und eine SQLite-Verbindung gehoert genau einem Strang.
    db = IndexJeStrang(index_pfad)
    stand = Lernstand(lernstand_pfad)
    kosten = Kosten(
        os.environ.get("TEACHBUDDY_KOSTEN") or lernstand_pfad.parent / "kosten.db"
    )
    app.config["KOSTEN"] = kosten
    app.config["INDEX"] = db
    app.config["LERNSTAND"] = stand
    app.config["INDEX_PFAD"] = str(index_pfad)

    # ----------------------------------------------------------------------
    # Lesen
    # ----------------------------------------------------------------------

    @app.get("/api/lernpfade")
    def _lernpfade():
        """Alle Lernpfade mit ihren Kapiteln.

        Die App holte bis zum 13.09.2026 fest verdrahtet ``P-01``. Mit dem
        zweiten Lernpfad waren dessen vier Kapitel und 29 Lektionen damit in
        der Oberflaeche unerreichbar — gebaut, aber unsichtbar.
        """
        return jsonify({"lernpfade": [
            d for d in (_lernpfad_daten(r["id"]) for r in
                        db.execute("SELECT id FROM pfade ORDER BY reihenfolge, id"))
            if d is not None
        ]})

    def _lernpfad_daten(pfad_id: str) -> dict[str, Any] | None:
        """Ein Lernpfad mit seinen Kapiteln. Eine Wahrheit fuer beide Routen."""
        pfad = abfragen.lernpfad(db, pfad_id)
        if pfad is None:
            return None

        staende = stand.alle()
        # BIB-26: Ein Kapitel hat mehrere Lektionen, eine Mindmap und einen
        # Gespraechspartner. Die Abschnitte A bis M sind die **Lektionen**;
        # bis zum 12.09.2026 wurden sie faelschlich als Kapitel ausgegeben.
        abschnitte = {a["schluessel"]: a for a in pfad["abschnitte"]}
        kapitel = []
        for k in db.execute(
            "SELECT * FROM kapitel WHERE pfad_id = ? ORDER BY nummer", (pfad_id,)
        ):
            kapitel.append({
                "id": k["id"],
                "nummer": k["nummer"],
                "titel": k["titel"],
                "kurzfassung": k["kurzfassung"] or "",
                "hat_mindmap": bool(_einheiten_des_kapitels(db, k["id"])),
                "hat_diskussion": bool(_einheiten_des_kapitels(db, k["id"])),
                "lektionen": _lektionen_des_kapitels(db, k["id"], abschnitte, staende),
            })

        antwort: dict[str, Any] = {
            "lernpfad": {
                "id": pfad["id"],
                "titel": pfad["titel"],
                "kurzfassung": pfad["kurzfassung"],
                "kapitel_gesamt": len(kapitel),
                "status": pfad["status"],
            },
            "kapitel": kapitel,
        }
        antwort["_herkunft"] = {
            "datei": pfad["pfad"],
            "index_gebaut_am": abfragen.meta(db).get("gebaut_am"),
        }
        ohne = [k["id"] for k in kapitel if not k["lektionen"]]
        if ohne:
            # Solange auch nur ein Abschnitt leer ist, steht hier warum.
            # Eine leere Liste ohne Begruendung ist eine Luege (TB-8).
            antwort["_fehlt"] = {
                "lektionen": "Diese Kapitel haben noch keine Lektion: "
                             + ", ".join(ohne),
            }
        return antwort

    @app.get("/api/lernpfad/<pfad_id>")
    def lernpfad(pfad_id: str):
        daten = _lernpfad_daten(pfad_id)
        if daten is None:
            return _nicht_da("lernpfad_unbekannt", f"Es gibt keinen Lernpfad {pfad_id}.")
        return jsonify(daten)

    @app.get("/api/lektion/<lektion_id>")
    def lektion(lektion_id: str):
        detail = _lektion_detail(db, stand, lektion_id)
        if detail is None:
            return _nicht_da(
                "lektion_unbekannt",
                f"Es gibt keine Lektion {lektion_id}.",
                offen=LEKTIONSSCHICHT_FEHLT,
            )
        return jsonify(detail)

    @app.get("/api/lektion/<lektion_id>/audio.mp3")
    def lektion_audio(lektion_id: str):
        """Liefert die Tonspur aus.

        Der Index haelt nur den Pfad relativ zur Bibliothek; die Datei wird
        von hier ausgeliefert, damit die App eine stabile Adresse hat.
        """
        from flask import send_file
        zeile = db.execute("SELECT audio_pfad FROM lektionen WHERE id = ?",
                           (lektion_id,)).fetchone()
        if zeile is None or not zeile["audio_pfad"]:
            return _nicht_da("audio_fehlt",
                             f"Zu {lektion_id} ist keine Tonspur hinterlegt.")
        datei = pfade.in_wissen(zeile["audio_pfad"])
        if datei is None or not datei.is_file():
            return _nicht_da(
                "audio_datei_fehlt",
                "Der Eintrag nennt %s, dort liegt nichts. Die Folge muss "
                "neu gebaut werden." % zeile["audio_pfad"])
        return send_file(datei, mimetype="audio/mpeg", conditional=True)

    @app.get("/api/lektion/<lektion_id>/bild.html")
    def lektion_bild(lektion_id: str):
        """Liefert die Uebersichtsgrafik als eigenstaendiges Dokument aus.

        Sie wird als Dokument eingebunden, nicht als Schnipsel kopiert: Die
        Grafik bringt eigene Klassennamen mit, und beides zu vermischen zerlegt
        beides (R-7, Punkt 3).
        """
        from flask import send_file
        z = db.execute("SELECT bild FROM lektion_zusatz WHERE lektion_id = ?",
                       (lektion_id,)).fetchone()
        if z is None or not z["bild"]:
            return _nicht_da("bild_fehlt", f"Zu {lektion_id} ist keine Grafik hinterlegt.")
        datei = pfade.in_wissen(z["bild"])
        if datei is None or not datei.is_file():
            return _nicht_da("bild_datei_fehlt",
                             "Der Eintrag nennt %s, dort liegt nichts." % z["bild"])
        return send_file(datei, mimetype="text/html")

    @app.get("/api/kapitel/<kapitel_id>/mindmap.html")
    def kapitel_mindmap_bild(kapitel_id: str):
        """Die gebaute Mindmap-Grafik (E-24a).

        Sie liegt als eigenstaendiges HTML-Dokument in der Bibliothek, genau wie das Bild
        einer Lektion, und wird als Dokument ausgeliefert statt in die Seite
        kopiert: Sie bringt eigene Klassennamen mit.
        """
        from flask import send_file
        z = db.execute(
            "SELECT bild FROM mindmap_analyse WHERE kapitel = ?", (kapitel_id,)
        ).fetchone()
        if z is None or not z["bild"]:
            return _nicht_da("mindmap_bild_fehlt",
                             f"Zu Kapitel {kapitel_id} ist keine Mindmap-Grafik hinterlegt.")
        datei = pfade.in_wissen(z["bild"])
        if datei is None or not datei.is_file():
            return _nicht_da("mindmap_bild_datei_fehlt",
                             "Der Eintrag nennt %s, dort liegt nichts." % z["bild"])
        return send_file(datei, mimetype="text/html")

    @app.get("/api/kapitel/<kapitel_id>/mindmap")
    def mindmap(kapitel_id: str):
        # Seit dem 12.09.2026 sind Kapitel-IDs eindeutig (BIB-26, 'K-01').
        # Vorher standen hier Abschnittsbuchstaben, die nur innerhalb eines
        # Lernpfads eindeutig waren; die Mehrdeutigkeitspruefung entfaellt.
        zeile = db.execute(
            "SELECT * FROM kapitel WHERE id = ?", (kapitel_id,)
        ).fetchone()
        if zeile is None:
            return _nicht_da("kapitel_unbekannt", f"Es gibt kein Kapitel {kapitel_id}.")

        we_ids = _einheiten_des_kapitels(db, kapitel_id)
        analyse = _mindmap_analyse(db, kapitel_id)
        kinder = abfragen.begriffsbaum(db, we_ids, analyse["achsen"] if analyse else None)
        staende = stand.alle()
        dauern = {
            r["id"]: float(r["dauer_sek"] or 0)
            for r in db.execute("SELECT id, dauer_sek FROM lektionen")
        }
        beleg_ids: list[str] = []
        _faerbe(kinder, staende, dauern, beleg_ids)

        antwort: dict[str, Any] = {
            "kapitel_id": kapitel_id,
            "titel": zeile["titel"],
            "zoomstufe": "kapitel",
            "wurzel": {
                "id": f"N-{kapitel_id}",
                # MMP-3 gilt auch fuer die Wurzel: Der Kapiteltitel ist ein
                # Satz, das Stichwort kommt aus der Strukturanalyse.
                "label": (analyse or {}).get("kern") or zeile["titel"],
                "satz": zeile["titel"],
                "art": "wurzel",
                "kurzfassung": (analyse or {}).get("kernaussage") or zeile["kurzfassung"] or "",
                "kinder": kinder,
            },
            # R-5/R-11: auch die Mindmap traegt ihre Belege ausgeschrieben.
            "belege": abfragen.belege_ausgeschrieben(db, beleg_ids),
        }
        if analyse and analyse.get("bild"):
            antwort["bild"] = analyse["bild"]
        if not kinder:
            antwort["_fehlt"] = {
                "knoten": LEKTIONSSCHICHT_FEHLT,
                "hinweis": (
                    "Der Knotenbaum wird aus den Wissenseinheiten und ihren "
                    "Voraussetzungen gebaut (MMP-1). Es fehlt nicht der Bau, "
                    "sondern die Zuordnung Einheit → Kapitel."
                ),
            }
        if analyse is None:
            # Ohne Analyse gibt es keine Achsen. Das wird gesagt, nicht
            # ausgeglichen — eine geratene Gliederung waere schlimmer als keine.
            antwort["_fehlt"] = dict(antwort.get("_fehlt") or {}, achsen=(
                "Fuer dieses Kapitel liegt keine Strukturanalyse vor "
                "(auftraege/mindmap-analyse.md). Die Knoten haengen deshalb "
                "nach Voraussetzung statt nach Gliederung."
            ))
        return jsonify(antwort)

    @app.get("/api/beleg/<beleg_id>")
    def beleg(beleg_id: str):
        daten = abfragen.beleg(db, beleg_id)
        if daten is None:
            return _nicht_da("beleg_unbekannt", f"Es gibt keinen Beleg {beleg_id}.")
        return jsonify(daten)

    # ----------------------------------------------------------------------
    # Schreiben (OBF-7)
    # ----------------------------------------------------------------------

    @app.put("/api/lektion/<lektion_id>/fortschritt")
    def fortschritt(lektion_id: str):
        daten = request.get_json(silent=True)
        if not isinstance(daten, dict):
            return _falsch("kein_json", "Erwartet wird ein JSON-Objekt.")
        try:
            position = float(daten.get("position_sek"))
        except (TypeError, ValueError):
            return _falsch("position_sek_fehlt", "position_sek muss eine Zahl sein.")
        fragen = daten.get("fragen", "offen")
        if fragen not in FRAGEN_ZUSTAENDE:
            return _falsch(
                "fragen_ungueltig",
                f"fragen muss eines von {list(FRAGEN_ZUSTAENDE)} sein, nicht {fragen!r}.",
            )
        ergebnis = stand.setze(lektion_id, position, fragen)
        if not ergebnis["uebernommen"]:
            return jsonify({"ok": False, **ergebnis}), 409
        return jsonify({"ok": True, "zeitpunkt": ergebnis["zeitpunkt"]})

    @app.post("/api/fortschritt/nachtrag")
    def nachtrag():
        daten = request.get_json(silent=True)
        if not isinstance(daten, list):
            return _falsch("keine_liste", "Erwartet wird eine Liste von Saetzen (APP-7).")
        ergebnis = stand.nachtrag(daten)
        ergebnis["_regel"] = (
            "Bei Konflikt gewinnt der spaetere Zeitpunkt. Der Server entscheidet, "
            "nicht der Browser."
        )
        return jsonify(ergebnis)

    @app.put("/api/einstellungen")
    def einstellungen():
        daten = request.get_json(silent=True)
        if not isinstance(daten, dict) or "tempo" not in daten:
            return _falsch("tempo_fehlt", "Erwartet wird { \"tempo\": … }.")
        try:
            tempo = float(daten["tempo"])
        except (TypeError, ValueError):
            return _falsch("tempo_ungueltig", "tempo muss eine Zahl sein.")
        unten, oben = TEMPO_GRENZEN
        if not unten <= tempo <= oben:
            return _falsch(
                "tempo_ausserhalb",
                f"tempo muss zwischen {unten} und {oben} liegen (OBF-10a).",
            )
        stand.setze_einstellung("tempo", repr(tempo))
        return jsonify({"ok": True, **stand.einstellungen()})

    @app.post("/api/frage/<frage_id>/antwort")
    def antwort(frage_id: str):
        daten = request.get_json(silent=True)
        if not isinstance(daten, dict) or not str(daten.get("text", "")).strip():
            return _falsch("text_fehlt", "Erwartet wird { \"text\": … }.")
        text = str(daten["text"]).strip()

        # Fragen als eigene Knoten gibt es in der Bibliothek noch nicht
        # (BIB-25). Was es gibt, ist die Prueffrage je Wissenseinheit — wird
        # deren ID geschickt, kommt sie samt ihren Belegen zurueck.
        einheit = abfragen.einheit(db, frage_id)
        belege = einheit["belege"] if einheit else []

        stand.merke_antwort(frage_id, text, "nicht_bewertbar", BEWERTUNG_FEHLT)
        antwort: dict[str, Any] = {
            "bewertung": "nicht_bewertbar",
            "begruendung": BEWERTUNG_FEHLT,
            "getroffen": [],
            "gefehlt": [],
            "belege": belege,
            "belege_ausgeschrieben": abfragen.belege_ausgeschrieben(db, belege),
            "gespeichert": True,
            "_offen": (
                "Die Antwortbewertung ist nicht gebaut. Erfunden wird sie nicht "
                "(CONTRIBUTING.md, Regel 2). Offen bleiben auszerdem PRF-1/PRF-4: "
                "Fragen mit eigener ID und Musterantwort gibt es in der "
                "Bibliothek noch nicht."
            ),
        }
        if einheit is None:
            antwort["_frage_unbekannt"] = (
                f"{frage_id} ist keine bekannte Wissenseinheit. Die Antwort ist "
                "trotzdem gespeichert — sie geht nicht verloren."
            )
        else:
            antwort["prueffrage"] = einheit["prueffrage"]
            antwort["wissenseinheit"] = einheit["id"]
        return jsonify(antwort)

    # ----------------------------------------------------------------------
    # Betrieb (nicht im Datenvertrag — siehe dienst/README.md)
    # ----------------------------------------------------------------------

    # -- Rueckmeldungen (OBF-19) -------------------------------------------

    ARTEN = ("unklar", "zu_lang", "falsch", "gut", "sonst")

    @app.post("/api/lektion/<lektion_id>/rueckmeldung")
    def rueckmeldung(lektion_id: str):
        """Eine Rueckmeldung des Menschen zu einer Einheit (OBF-19).

        **Die Fassung wird mitgeschrieben, nicht nachgeschlagen** (AUF-18a).
        Eine Rueckmeldung gilt fuer den Stand, den er gehoert hat. Liest man
        sie spaeter gegen die dann aktuelle Fassung, deutet man sie falsch —
        „klingt sperrig" heisst etwas anderes, wenn die Folge zwei
        Nachbesserungen alt ist.
        """
        daten = request.get_json(silent=True)
        if not isinstance(daten, dict):
            return _falsch("rumpf_fehlt", 'Erwartet wird { "art": … }.')
        art = str(daten.get("art") or "sonst").strip()
        if art not in ARTEN:
            return _falsch("art_unbekannt",
                           "art muss eines von %s sein." % ", ".join(ARTEN))
        text = str(daten.get("text") or "").strip() or None
        if art == "sonst" and not text:
            return _falsch("text_fehlt",
                           'Bei art "sonst" gehoert ein Text dazu.')

        zusatz = db.execute(
            "SELECT pipeline, erzeugt FROM lektion_zusatz WHERE lektion_id = ?",
            (lektion_id,)).fetchone()
        if zusatz is None and db.execute(
                "SELECT 1 FROM lektionen WHERE id = ?",
                (lektion_id,)).fetchone() is None:
            # Eine fehlende Lektion ist nichts Falsches an der Anfrage,
            # sondern eine fehlende Sache — 404, nicht 400.
            return _nicht_da("lektion_unbekannt", f"{lektion_id} gibt es nicht.")

        einheit_id = str(daten.get("einheit") or "").strip() or None
        gemerkt = stand.merke_rueckmeldung(
            lektion_id,
            einheit_id=einheit_id,
            art=art,
            text=text,
            pipeline=zusatz["pipeline"] if zusatz is not None else None,
            erzeugt=zusatz["erzeugt"] if zusatz is not None else None,
        )
        return jsonify({"gemerkt": True, **gemerkt})

    @app.get("/api/rueckmeldungen")
    def alle_rueckmeldungen():
        """Was zusammengekommen ist — nach Fassung lesbar."""
        lektion = request.args.get("lektion")
        offen = request.args.get("offen") in ("1", "true", "ja")
        return jsonify({"rueckmeldungen": stand.rueckmeldungen(lektion, offen=offen)})

    @app.get("/api/zustand")
    def zustand():
        meta = abfragen.meta(db)
        alle = abfragen.befunde(db)
        nach_schwere: dict[str, int] = {}
        for f in alle:
            nach_schwere[f["schwere"]] = nach_schwere.get(f["schwere"], 0) + 1
        return jsonify(
            {
                "index": {"pfad": app.config["INDEX_PFAD"], **meta},
                "lernstand": {
                    "pfad": str(stand.pfad),
                    "lektionen_mit_stand": len(stand.alle()),
                    **stand.einstellungen(),
                },
                "befunde": nach_schwere,
                "fehler": [f for f in alle if f["schwere"] == "fehler"],
            }
        )

    # ----------------------------------------------------------------------
    # Kosten (E-21) — keine Obergrenze, dafuer volle Sichtbarkeit.
    # Ohne Grenze ist die Anzeige die einzige Kontrolle, also Pflicht.
    # ----------------------------------------------------------------------

    @app.get("/api/einstellungen")
    def _einstellungen_lesen():
        """Der Leseweg zu dem, was bisher nur geschrieben werden konnte.

        R-15 hat das Abspieltempo zum Lernstand erklaert, der Vertrag kannte
        aber nur `PUT`. Die App las es behelfsweise aus `/api/zustand`, das
        dafuer nicht gedacht ist (dort steht der Zustand des Dienstes, nicht
        der des Lernenden).
        """
        return jsonify(stand.einstellungen())

    # ----------------------------------------------------------------------
    # Sprachgespraech (E-20). Der Browser haelt die Audioverbindung selbst —
    # ueber den Server zu leiten fuegte genau die Latenz hinzu, derentwegen der
    # Server-Weg verworfen wurde (E-20a). Der Server gibt nur ein kurzlebiges Token
    # heraus; der langlebige Schluessel bleibt hier.
    # ----------------------------------------------------------------------

    @app.post("/api/kapitel/<kapitel_id>/sprachsitzung")
    def _sprachsitzung(kapitel_id: str):
        import secrets
        import urllib.error
        import urllib.request

        import zugang

        # **Der Browser sagt, was er kann.** Werkzeuge nuetzen nur, wenn
        # jemand sie ausfuehrt, und das tut der Browser (E-20a). Kann er es
        # nicht, darf der Partner sie nicht angeboten bekommen.
        #
        # Am 14.09.2026 ist genau das schiefgegangen: Der Server war neu, der
        # Browser hatte noch die alte `gespraech.js` aus dem Service-Worker-
        # Mantel. Der Partner rief ein Werkzeug, niemand antwortete, er
        # wartete — und nach fuenfzehn Sekunden Stille schloss die Sitzung.
        # Aus die Sicht: „kaputt, er schliesst einfach und antwortet auch
        # nicht."
        #
        # Ein Neuladen haette es behoben und ist die falsche Antwort: Der
        # Service Worker laesst einen neuen Mantel absichtlich warten, bis
        # keine alte Seite mehr offen ist (das ist richtig so). Also darf die
        # Sitzung nicht davon abhaengen, welche Fassung gerade im Browser
        # liegt. Ein alter Browser bekommt ein Gespraech ohne Werkzeuge — das
        # ist aermer, aber es laeuft.
        wunsch = request.get_json(silent=True) or {}
        kann_werkzeuge = bool(wunsch.get("werkzeuge"))
        # Ins Journal, damit nie wieder geraten werden muss, welche Fassung
        # der Browser hatte. Am 14.09.2026 habe ich das dreimal aus indirekten
        # Spuren erschlossen, statt es einfach dastehen zu haben.
        app.logger.info("Sprachsitzung %s: Browser %s Werkzeuge",
                        kapitel_id, "mit" if kann_werkzeuge else "OHNE")

        we_ids = _einheiten_des_kapitels(db, kapitel_id)
        if not we_ids:
            return _nicht_da(
                "kapitel_ohne_inhalt",
                f"Kapitel {kapitel_id} hat keine Wissenseinheiten. Ein Gespraech "
                "ohne Kapitelkontext waere ein freier Chatbot (APP-12).")

        schluessel = zugang.hole("openai_key", pflicht=False)
        if not schluessel:
            return _falsch(
                "kein_schluessel",
                "Fuer das Sprachgespraech fehlt der OpenAI-Zugang. "
                "Setze TEACHBUDDY_OPENAI_API_KEY in .env.")

        # Der Kapitelkontext geht vollstaendig mit (OBF-14, E-20b): Ein Kapitel
        # liegt weit unter der Grenze, ab der sich Abruf lohnt (E-9). Alles
        # mitzugeben ist hier kein Notbehelf, sondern der bessere Weg — es gibt
        # kein Retrieval, das etwas uebersehen koennte.
        anweisung = _gespraechs_anweisung(
            db, kapitel_id, we_ids, stand.sitzungen_zum_kapitel(kapitel_id),
            mit_werkzeugen=kann_werkzeuge)

        sitzung_id = "S-" + secrets.token_hex(6)
        preis = zugang.preis_pro_minute()
        kosten.sitzung_beginnt(sitzung_id, kapitel_id, preis, zugang.waehrung())

        # GA-Endpunkt seit 2026: /v1/realtime/client_secrets. Der alte Weg
        # /v1/realtime/sessions antwortet mit 404 — daran scheitern alle
        # Anleitungen aus der Beta-Zeit.
        rumpf = json.dumps({
            "session": {
                "type": "realtime",
                "model": os.environ.get("TEACHBUDDY_REALTIME_MODELL", "gpt-realtime"),
                "audio": {
                    "output": {"voice": os.environ.get(
                        "TEACHBUDDY_REALTIME_STIMME", "alloy")},
                    # Ohne eingeschaltete Mitschrift schickt der Anbieter keine
                    # Abschrift der Nutzerrede — dann bliebe das Gedaechtnis
                    # einseitig und der Verlauf halb.
                    "input": {
                        "transcription": {"model": os.environ.get(
                            "TEACHBUDDY_MITSCHRIFT_MODELL",
                            "gpt-4o-mini-transcribe")},
                        # **Wie lange Stille heisst, dass er fertig ist.**
                        # Ohne diesen Block gilt die Voreinstellung von etwa
                        # einer halben Sekunde. In die Sitzung vom 14.09.
                        # (14:42-14:47) hat der Partner ihm sechsmal ins Wort
                        # gefallen — „Stopp, lass", „Moment, lass uns",
                        # „Warte mal kurz" —, jedes Mal waehrend der Nutzer noch
                        # formulierte: „Ugh." … „Um…" … „irgendwie…".
                        #
                        # Gefuellte Pausen sind fuer die Spracherkennung
                        # Sprache mit Luecken dazwischen. Wer denkt, waehrend
                        # er redet, braucht laengere Luecken als eine halbe
                        # Sekunde — und dieser Partner ist fuer Leute da, die
                        # nachdenken, nicht fuer Diktate.
                        #
                        # Der Preis: Der Partner setzt einen Wimpernschlag
                        # spaeter ein. Das ist der bessere Fehler.
                        "turn_detection": {
                            "type": "server_vad",
                            "silence_duration_ms": int(os.environ.get(
                                "TEACHBUDDY_PAUSE_MS", "1000")),
                            "prefix_padding_ms": 300,
                            "threshold": 0.5,
                            # Beides muss ausdruecklich dastehen: Wer
                            # turn_detection selbst setzt, erbt die
                            # Voreinstellungen nicht mit.
                            "create_response": True,
                            "interrupt_response": True,
                        },
                    },
                },
                "instructions": anweisung,
                # DIS-24/DIS-25: Der Partner ruft, der Server antwortet. Bis zum
                # 14.09.2026 stand hier nichts — er konnte nur mit dem
                # arbeiten, was in der Anweisung stand, und die ist bei einem
                # grossen Kapitel gekuerzt. Rückmeldung: "er kann keine Recherche zu
                # weiterfuehrenden Fragen, das hatten wir aber so vereinbart".
                "tools": werkzeuge_mod.ERKLAERUNGEN if kann_werkzeuge else [],
                "tool_choice": "auto" if kann_werkzeuge else "none",
            }
        }).encode("utf-8")
        anfrage = urllib.request.Request(
            "https://api.openai.com/v1/realtime/client_secrets", data=rumpf,
            headers={"Authorization": f"Bearer {schluessel}",
                     "Content-Type": "application/json"},
            method="POST")
        try:
            with urllib.request.urlopen(anfrage, timeout=20) as antwort:
                sitzung = json.loads(antwort.read())
        except urllib.error.HTTPError as fehler:
            return _falsch("anbieter_lehnt_ab",
                           "Der Anbieter antwortet mit %s: %s"
                           % (fehler.code, fehler.read()[:300].decode("utf-8", "replace")))
        except urllib.error.URLError as fehler:
            return _falsch("anbieter_nicht_erreichbar", str(fehler.reason))

        # Die GA-Antwort traegt den Wert flach in `value`, die Sitzung darunter.
        innen = sitzung.get("session") or {}
        return jsonify({
            "sitzung_id": sitzung_id,
            "token": sitzung.get("value") or (sitzung.get("client_secret") or {}).get("value"),
            "ablauf": sitzung.get("expires_at"),
            "modell": innen.get("model"),
            "stimme": ((innen.get("audio") or {}).get("output") or {}).get("voice"),
            # Wohin der Browser den SDP-Handschlag schickt (GA: /v1/realtime/calls).
            "verbindung": "https://api.openai.com/v1/realtime/calls",
            "preis_pro_minute": preis,
            "waehrung": zugang.waehrung(),
            # OBF-13c: Die Uhr laeuft auch in Denkpausen (E-20c).
            "stille_abschaltung_sek": 15,
        })

    @app.post("/api/sitzung/<sid>/werkzeug")
    def _werkzeug(sid: str):
        """Der eine Weg, auf dem der Partner den Server erreicht (DIS-24).

        Ein Verteiler statt vier Endpunkte: Der Browser reicht durch, was der
        Anbieter ihm als Funktionsaufruf gibt, und schickt das Ergebnis
        zurueck. Je Werkzeug eine eigene Adresse haette im Browser eine
        Zuordnungstabelle verlangt, die dann neben dieser hier verrottet.

        **Fehler werden als Ergebnis zurueckgegeben, nicht als Statuscode.**
        Ein Werkzeug, das mit 500 antwortet, laesst den Partner mitten im Satz
        raten. Er soll sagen koennen, dass es nicht ging (TB-8).
        """
        daten = request.get_json(silent=True) or {}
        name = str(daten.get("werkzeug") or "")
        arg = daten.get("argumente") or {}
        if not isinstance(arg, dict):
            arg = {}
        kapitel_id = str(daten.get("kapitel") or "") or None

        if name == "bibliothek_nachschlagen":
            return jsonify(werkzeuge_mod.nachschlagen(db, str(arg.get("frage") or "")))

        if name == "recherchieren":
            import zugang
            frage = str(arg.get("frage") or "").strip()
            if not frage:
                return jsonify({"fehler": "frage_fehlt"})
            schluessel = zugang.hole("openai_key", pflicht=False)
            if not schluessel:
                return jsonify({
                    "fehler": "kein_schluessel",
                    "hinweis": "Kein Zugang zur Suche. Sag das im Gespraech."})
            import time
            t0 = time.monotonic()
            ergebnis = werkzeuge_mod.recherchieren(frage, schluessel)
            dauer = time.monotonic() - t0
            # E-21: Der Aufruf kostet Geld, also wird er gezaehlt — auch der
            # gescheiterte, denn der kostet Wartezeit im Gespraech.
            kosten.recherche(sitzung_id=sid, kapitel_id=kapitel_id,
                             modell=werkzeuge_mod.RECHERCHE_MODELL, sekunden=dauer)
            # DIS-28/DIS-30: Was live nachgesehen wurde, wird festgehalten —
            # im Rueckkanal, nicht in der Bibliothek.
            if not ergebnis.get("fehler"):
                stand.merke_recherche(frage, sitzung_id=sid, kapitel_id=kapitel_id,
                                      antwort=ergebnis.get("antwort"))
            return jsonify(ergebnis)

        if name == "rechercheauftrag_aufnehmen":
            frage = str(arg.get("frage") or "").strip()
            if not frage:
                return jsonify({"fehler": "frage_fehlt"})
            stand.merke_recherche(
                frage, sitzung_id=sid, kapitel_id=kapitel_id,
                zusammenhang=str(arg.get("zusammenhang") or "") or None,
                auftrag=True)
            return jsonify({"aufgenommen": True})

        if name == "punkt_geprueft":
            punkt = str(arg.get("id") or "").strip()
            urteil = str(arg.get("urteil") or "").strip()
            if urteil not in ("sitzt", "halb", "offen"):
                return jsonify({"fehler": "urteil_unbekannt"})
            if not punkt:
                return jsonify({"fehler": "punkt_fehlt"})
            return jsonify(stand.merke_agenda(
                sid, punkt, urteil, str(arg.get("begruendung") or "") or None))

        return jsonify({"fehler": "werkzeug_unbekannt", "werkzeug": name})

    @app.get("/api/recherchen")
    def _recherchen():
        """Was im Gespraech nachgesehen und was als Luecke geparkt wurde."""
        return jsonify({"recherchen": stand.recherchen(
            request.args.get("kapitel"),
            nur_auftraege=request.args.get("auftraege") in ("1", "true", "ja"))})

    @app.get("/api/kapitel/<kapitel_id>/agenda")
    def _agenda(kapitel_id: str):
        """DIS-14: die Punkte, die beruehrt werden sollen. Ohne Reihenfolge."""
        we_ids = _einheiten_des_kapitels(db, kapitel_id)
        if not we_ids:
            return _nicht_da("kapitel_ohne_inhalt", f"Kapitel {kapitel_id} ist leer.")
        zeilen = db.execute(
            "SELECT id, titel, prueffrage FROM einheiten WHERE id IN (%s)"
            % ",".join("?" * len(we_ids)), we_ids)
        punkte = [
            {"id": "AG-" + z["id"], "wissenseinheit": z["id"],
             "titel": z["titel"], "frage": (z["prueffrage"] or "").strip(),
             "zustand": "offen"}
            for z in zeilen if (z["prueffrage"] or "").strip()
        ]
        return jsonify({"kapitel_id": kapitel_id, "punkte": punkte,
                        "_zustaende": "offen | sitzt | halb | sitzt_nicht"})

    @app.get("/api/kosten")
    def _kosten():
        import zugang
        return jsonify(kosten.uebersicht(waehrung=zugang.waehrung()))

    @app.post("/api/sitzung/<sid>/beginn")
    def _sitzung_beginn(sid: str):
        daten = request.get_json(silent=True) or {}
        kapitel = daten.get("kapitel_id")
        if not kapitel:
            return _falsch("kapitel_id_fehlt", "Eine Sitzung gehoert zu einem Kapitel (OBF-13).")
        import zugang
        preis = zugang.preis_pro_minute()
        kosten.sitzung_beginnt(sid, kapitel, preis, zugang.waehrung())
        return jsonify({"sitzung_id": sid, "preis_pro_minute": preis,
                        "waehrung": zugang.waehrung(),
                        "stille_abschaltung_sek": 15})

    @app.post("/api/sitzung/<sid>/ende")
    def _sitzung_ende(sid: str):
        daten = request.get_json(silent=True) or {}
        sek = daten.get("sekunden")
        if sek is None:
            # E-20c: Gezaehlt wird die offene Verbindung, nicht die Sprechzeit.
            return _falsch("sekunden_fehlen",
                           "Gemeldet wird die offene Sitzungsdauer, auch die Stille darin (E-20c).")
        kosten.sitzung_endet(sid, float(sek))
        return jsonify({"ok": True})

    @app.post("/api/sitzung/<sid>/mitschrift")
    def _sitzung_mitschrift(sid: str):
        """Nimmt entgegen, was im Gespraech gesagt wurde (R-16, DIS-30).

        Der Server hoert nicht mit: Der Ton laeuft direkt vom Browser zum Anbieter
        (E-20a). Ohne diese Meldung gibt es keinen Verlauf und damit kein
        Gedaechtnis ueber Sitzungen hinweg.
        """
        d = request.get_json(silent=True) or {}
        kapitel = d.get("kapitel_id")
        beitraege = d.get("beitraege")
        if not kapitel:
            return _falsch("kapitel_id_fehlt", "Eine Mitschrift gehoert zu einem Kapitel.")
        if not isinstance(beitraege, list):
            return _falsch("beitraege_fehlen", "Erwartet wird eine Liste von Beitraegen.")
        anzahl = stand.merke_beitraege(sid, kapitel, beitraege)
        return jsonify({"ok": True, "gemerkt": anzahl})

    @app.get("/api/sitzung/<sid>/verlauf")
    def _sitzung_verlauf(sid: str):
        beitraege = stand.verlauf(sid)
        antwort = {"sitzung_id": sid, "beitraege": beitraege}
        if not beitraege:
            # Ehrlich sein, statt eine leere Liste als "es wurde nichts
            # gesagt" auszugeben (TB-8).
            antwort["_fehlt"] = {"mitschrift": (
                "Zu dieser Sitzung ist keine Mitschrift eingegangen. Der Server "
                "hoert nicht mit (E-20a); ob nichts gesprochen wurde oder die "
                "Meldung ausblieb, ist von hier aus nicht zu unterscheiden."
            )}
        return jsonify(antwort)

    @app.post("/api/vertonung")
    def _vertonung():
        """Meldet eine fertig vertonte Folge (POD-7a).

        Der Podcast-Bauer laeuft ausserhalb des Dienstes; er meldet hierher,
        was er verbraucht hat. Ohne diese Meldung waere die Zahl je Lernpfad
        (E-21d) nicht zu bilden.
        """
        d = request.get_json(silent=True) or {}
        if not d.get("auftrag_id") or d.get("zeichen") is None:
            return _falsch("unvollstaendig", "auftrag_id und zeichen sind Pflicht.")
        kosten.vertonung(d["auftrag_id"], int(d["zeichen"]),
                         lernpfad_id=d.get("lernpfad_id"),
                         lektion_id=d.get("lektion_id"),
                         preis_1k=float(d.get("preis_1k", 0.0)))
        return jsonify({"ok": True})

    @app.errorhandler(404)
    def _vierhundertvier(_):
        return jsonify({"fehler": "unbekannter_weg", "grund": request.path}), 404

    return app


# --------------------------------------------------------------------------
# Bausteine
# --------------------------------------------------------------------------


def _einheiten_des_kapitels(db, kapitel_id: str) -> list[str]:
    """Die Wissenseinheiten eines Kapitels — ueber die Lektionen des Kapitels.

    Heute leer: Es gibt keine Lektionen (siehe ``LEKTIONSSCHICHT_FEHLT``).
    Die Abfrage steht trotzdem hier und nicht als Sonderfall im Endpunkt,
    damit der Tag, an dem Lektionsdateien entstehen, keine Codeaenderung
    braucht.
    """
    rows = db.execute(
        "SELECT DISTINCT le.einheit_id AS id"
        "  FROM lektion_einheiten le"
        "  JOIN lektionen l ON l.id = le.lektion_id"
        " WHERE l.kapitel = ?"
        " ORDER BY le.rang",
        (kapitel_id,),
    )
    return [r["id"] for r in rows]


def _lektionen_des_kapitels(db, kapitel_id: str, abschnitte: dict, staende: dict) -> list[dict]:
    """Alle Lektionen eines Kapitels, gebaute und geplante, in Reihenfolge.

    **Geplante kommen mit.** Das Kapitel hat dreizehn Lektionen; gebaut ist
    eine. Nur die eine zu zeigen, hiesse, das Kapitel sei fertig. Was fehlt,
    steht mit seinem Titel da und sagt, dass es die Folge noch nicht gibt
    (TB-8).
    """
    gebaut = {
        r["abschnitt"]: dict(r)
        for r in db.execute("SELECT * FROM lektionen WHERE kapitel = ?", (kapitel_id,))
    }
    raus = []
    for rang, zeile in enumerate(db.execute(
        "SELECT abschnitt FROM kapitel_lektionen WHERE kapitel_id = ? ORDER BY rang",
        (kapitel_id,),
    ), start=1):
        schluessel = zeile["abschnitt"]
        if schluessel in gebaut:
            raus.append(_lektion_kurz(gebaut[schluessel], staende, db))
            continue
        a = abschnitte.get(schluessel) or {}
        raus.append({
            "id": None,
            "abschnitt": schluessel,
            "nummer": rang,
            "titel": a.get("titel") or schluessel,
            "kurzfassung": a.get("kern") or "",
            "geplant": True,
        })
    return raus


def _lektion_kurz(zeile: dict, staende: dict, db=None) -> dict[str, Any]:
    stand = staende.get(zeile["id"])
    position = float(stand["position_sek"]) if stand else 0.0
    dauer = float(zeile["dauer_sek"] or 0)
    return {
        "id": zeile["id"],
        "abschnitt": zeile.get("abschnitt"),
        "nummer": zeile["nummer"],
        "titel": zeile["titel"],
        "geplant": False,
        # **Dritter Zustand.** Eine Lektion kann Wissen haben und trotzdem
        # keine Folge: Der Podcast-Bauer lehnt ab, wenn das Material keine
        # fuenf bis zehn Minuten traegt. Dann ist `dauer_sek` die *geplante*
        # Dauer, und die Oberflaeche zeigte sie als waere sie gemessen.
        "hat_ton": bool(zeile.get("audio_pfad")),
        "dauer_sek": zeile["dauer_sek"],
        "position_sek": position,
        "gehoert_anteil": _anteil(position, dauer),
        "fragen": stand["fragen"] if stand else "offen",
        # Das Vorschaubild gehoert in die Kurzform: Die Kapitelliste zeigt es,
        # und ein Nachladen je Zeile waere ein Aufruf pro Lektion.
        "bild": _bild_von(db, zeile["id"]) if db is not None else None,
    }


def _anteil(position: float, dauer: float) -> float:
    """R-4: zwei unabhaengige Achsen, kein Leiterzustand.

    Der Anzeigezustand wird im Frontend abgeleitet; hier faellt nur die Zahl
    an. Die Schwelle 0,95 steht in ``GEHOERT_SCHWELLE`` und wird hier nicht
    angewendet — sie gehoert zur Anzeige, nicht zum Wert.
    """
    if dauer <= 0:
        return 0.0
    return round(min(position / dauer, 1.0), 4)


def _lektion_detail(db, stand: Lernstand, lektion_id: str) -> dict[str, Any] | None:
    """Das Lektionsdetail nach Datenvertrag v2 — mit ausgeschriebenen Belegen.

    Ist heute ohne Treffer, weil es keine Lektionsdateien gibt. Der Weg ist
    vollstaendig gebaut: Sobald eine Lektion ihre Wissenseinheiten nennt
    (BIB-27), traegt dieselbe Funktion Folienpunkte, Quellen und Belege
    zusammen.
    """
    zeile = db.execute("SELECT * FROM lektionen WHERE id = ?", (lektion_id,)).fetchone()
    if zeile is None:
        return None

    we_ids = [
        r["einheit_id"]
        for r in db.execute(
            "SELECT einheit_id FROM lektion_einheiten WHERE lektion_id = ? ORDER BY rang",
            (lektion_id,),
        )
    ]
    punkte: list[dict[str, Any]] = []
    # POD-13 verlangt eine Stichwortunterlage, keine Prosa. `folie_punkte`
    # liefert die Absaetze des Inhalts — das ist der Volltext und damit die
    # Textwand, die am 13.09.2026 gemeldet wurde. Der Kopf einer Einheit
    # ist dagegen schon modelliert: `stichwort` (zwei bis vier Woerter,
    # E-24), `titel` (die Behauptung als ein Satz) und `kurzfassung`.
    #
    # Hier wird also nichts erzeugt, nur herausgegeben, was die Bibliothek
    # ohnehin fuehrt. Die Folie kann damit die Kernaussage zeigen und die
    # Prosa dahinter wegklappen, statt alles gleichzeitig hinzulegen.
    koepfe: list[dict[str, Any]] = []
    for wid in we_ids:
        einheit = abfragen.einheit(db, wid)
        if einheit is None:
            continue
        eigene = folie_punkte(einheit["inhalt"])
        for punkt in eigene:
            punkt["wissenseinheit"] = wid
            punkte.append(punkt)
        koepfe.append({
            "id": wid,
            "stichwort": einheit["stichwort"],
            "titel": einheit["titel"],
            "kurzfassung": einheit["kurzfassung"],
            "grad": einheit["grad"],
            # POD-14: jede Kernaussage traegt ihren Belegverweis. Die Belege
            # der Einheit sind die ihrer Absaetze, in ihrer Reihenfolge.
            "belege": list(dict.fromkeys(
                b for punkt in eigene for b in punkt["belege"])),
        })

    beleg_ids = list(dict.fromkeys(b for p in punkte for b in p["belege"]))
    belege = abfragen.belege_ausgeschrieben(db, beleg_ids)
    quellen = _quellen_zu(db, beleg_ids)

    zusatz = db.execute(
        "SELECT pipeline, erzeugt FROM lektion_zusatz WHERE lektion_id = ?",
        (lektion_id,)).fetchone()

    eigener_stand = stand.fortschritt(lektion_id)
    position = float(eigener_stand["position_sek"]) if eigener_stand else 0.0
    dauer = float(zeile["dauer_sek"] or 0)

    return {
        "id": zeile["id"],
        "kapitel_id": zeile["kapitel"],
        "titel": zeile["titel"],
        "dauer_sek": zeile["dauer_sek"],
        "position_sek": position,
        "gehoert_anteil": _anteil(position, dauer),
        "fragen": eigener_stand["fragen"] if eigener_stand else "offen",
        "audio_url": f"/api/lektion/{lektion_id}/audio.mp3" if zeile["audio_pfad"] else None,
        # R-10: Die Marke traegt ihre Bedeutung in `art`, nicht im Titeltext.
        "kapitelmarken": [
            {"sek": m["sek"], "titel": m["titel"], "art": m["art"]}
            for m in db.execute(
                "SELECT sek, titel, art FROM kapitelmarken"
                " WHERE lektion_id = ? ORDER BY sek", (lektion_id,))
        ],
        "bild": _bild_von(db, lektion_id),
        # Die Fragen kommen aus den Wissenseinheiten der Lektion: Der
        # Modellierer schreibt je Einheit eine Pruefrage, deren Antwort zeigt,
        # ob die Einheit verstanden ist (AUF-1, Modellierer-Auftrag). Sie hier
        # zu sammeln ist keine Erfindung, sondern eine Zusammenstellung.
        "fragenblock": _fragen_von(db, we_ids, belege),
        "folie_punkte": punkte,
        # Der Kopf je Einheit — die Folie gliedert sich danach (POD-13).
        "einheiten": koepfe,
        # AUF-18a: Womit diese Folge gebaut wurde. `nummer` kommt aus der
        # Bibliothek, der Klartext aus dem Register. Fehlt die Nummer, ist
        # die Folge aelter als die Zaehlung — dann wird das gesagt und
        # nicht geraten.
        "pipeline": _pipeline_von(zusatz),
        "wissenseinheiten": we_ids,
        "quellen": quellen,
        # R-5: ausgeschrieben, nicht nachzuladen.
        "belege": belege,
    }


def _pipeline_von(zusatz) -> dict[str, Any]:
    """Fassung und Tag der Erzeugung, fuer den Menschen lesbar (AUF-18a)."""
    nummer = zusatz["pipeline"] if zusatz is not None else None
    erzeugt = zusatz["erzeugt"] if zusatz is not None else None
    if not nummer:
        return {
            "nummer": None,
            "erzeugt": erzeugt,
            "was": [],
            "regeln": [],
            "jetzige": fassung_mod.JETZIGE.nummer,
            "hinweis": "Diese Folge ist vor der Fassungszaehlung entstanden.",
        }
    f = next((x for x in fassung_mod.FASSUNGEN if x.nummer == nummer), None)
    return {
        "nummer": nummer,
        "erzeugt": erzeugt,
        "datum": f.datum if f else None,
        "was": list(f.was) if f else [],
        "regeln": list(f.regeln) if f else [],
        "jetzige": fassung_mod.JETZIGE.nummer,
        "aktuell": nummer == fassung_mod.JETZIGE.nummer,
    }


def _fragen_von(db, we_ids: list[str], belege: dict) -> list[dict[str, Any]]:
    """Die Pruefragen der Wissenseinheiten dieser Lektion.

    PRF-1 verlangt, dass jede Frage auf Belege zurueckgeht und die
    Musterantwort in der Bibliothek steht. Beides ist hier erfuellt, ohne dass
    etwas erzeugt werden muesste: Die Frage steht in der Einheit, die
    Musterantwort ist ihre Kurzfassung, die Belege sind die der Einheit.
    """
    if not we_ids:
        return []
    zeilen = db.execute(
        "SELECT id, titel, prueffrage, kurzfassung FROM einheiten WHERE id IN (%s)"
        % ",".join("?" * len(we_ids)), we_ids)
    nach_id = {z["id"]: z for z in zeilen}
    fragen = []
    for wid in we_ids:                      # Reihenfolge der Lektion, nicht der Datenbank
        z = nach_id.get(wid)
        if z is None or not (z["prueffrage"] or "").strip():
            continue
        eigene = [b for b, d in belege.items() if wid in (d.get("einheiten") or [wid])]
        fragen.append({
            "id": f"F-{wid}",
            "wissenseinheit": wid,
            "frage": z["prueffrage"].strip(),
            "musterantwort": (z["kurzfassung"] or "").strip(),
            "belege": eigene[:4],
        })
    return fragen


def _mindmap_analyse(db, kapitel_id: str) -> dict[str, Any] | None:
    """Die Strukturanalyse eines Kapitels (E-19a), oder None.

    Sie gibt der Mindmap ihre Gliederung. Fehlt sie, wird nichts geraten.
    """
    kopf = db.execute(
        "SELECT * FROM mindmap_analyse WHERE kapitel = ?", (kapitel_id,)
    ).fetchone()
    if kopf is None:
        return None
    achsen = []
    for a in db.execute(
        "SELECT * FROM mindmap_achsen WHERE kapitel = ? ORDER BY rang", (kapitel_id,)
    ):
        achsen.append({
            "id": a["achse_id"],
            "frage": a["frage"],
            # MMP-10a: Ist die Analyse zweistufig, haengt die Achse unter
            # ihrer Elternachse statt gleichrangig an der Wurzel.
            "eltern": a["eltern"],
            "eltern_frage": a["eltern_frage"],
            "einheiten": [
                r["einheit_id"]
                for r in db.execute(
                    "SELECT einheit_id FROM mindmap_achse_einheiten"
                    " WHERE kapitel = ? AND achse_id = ? ORDER BY rang",
                    (kapitel_id, a["achse_id"]),
                )
            ],
        })
    bild = None
    if kopf["bild"]:
        try:
            belege = json.loads(kopf["bild_belege"] or "[]")
        except (TypeError, ValueError):
            belege = []
        bild = {
            "url": f"/api/kapitel/{kapitel_id}/mindmap.html",
            "breite": kopf["bild_breite"],
            "hoehe": kopf["bild_hoehe"],
            "titel": kopf["bild_titel"],
            "belege": belege,
        }
    return {
        "kern": kopf["kern"],
        "kernaussage": kopf["kernaussage"],
        "beziehungen": kopf["beziehungen"],
        "layout": kopf["layout"],
        "achsen": achsen,
        "bild": bild,
    }


def _bild_von(db, lektion_id: str) -> dict[str, Any] | None:
    """Die Uebersichtsgrafik der Lektion (OBF-9, R-7).

    ``breite`` und ``hoehe`` stehen mit dabei, obwohl sie im Dokument selbst
    stehen: Ohne sie kennt die App das Seitenverhaeltnis erst nach dem Laden,
    und dann springt das Layout.

    ``belege`` am Bild ist kein Schmuck. Der Grafik-Befund fuehrt "ein Bild
    traegt keine Beleg-ID" als ersten bleibenden Grund gegen erzeugte Bilder
    auf; der Code-Weg kann es, also tut er es.
    """
    z = db.execute(
        "SELECT bild, bild_breite, bild_hoehe, bild_titel, bild_belege"
        "  FROM lektion_zusatz WHERE lektion_id = ?", (lektion_id,)).fetchone()
    if z is None or not z["bild"]:
        return None
    try:
        belege = json.loads(z["bild_belege"] or "[]")
    except (TypeError, ValueError):
        belege = []
    return {
        "url": f"/api/lektion/{lektion_id}/bild.html",
        "breite": z["bild_breite"],
        "hoehe": z["bild_hoehe"],
        "titel": z["bild_titel"],
        "belege": belege,
    }


def _quellen_zu(db, beleg_ids: list[str]) -> list[dict[str, Any]]:
    if not beleg_ids:
        return []
    platz = ",".join("?" * len(beleg_ids))
    rows = db.execute(
        f"""
        SELECT DISTINCT q.id, q.titel, q.urheber, q.veroeffentlicht, q.fundort,
               q.qualitaet, q.reichweite
          FROM belege b
          JOIN fundstellen f ON f.id = b.fundstelle_id
          JOIN quellen     q ON q.id = f.quelle_id
         WHERE b.id IN ({platz})
         ORDER BY q.id
        """,
        beleg_ids,
    )
    return [
        {
            "id": r["id"],
            "titel": r["titel"],
            "urheber": r["urheber"],
            "jahr": (r["veroeffentlicht"] or "")[:4] or None,
            "fundort": r["fundort"],
            "art": r["qualitaet"],
            "reichweite": r["reichweite"],
        }
        for r in rows
    ]


def _faerbe(knoten: list[dict], staende: dict, dauern: dict, beleg_ids: list[str]) -> None:
    """Setzt den Lernstand an die Mindmap-Knoten (MMP-7) und sammelt Belege."""
    for k in knoten:
        beleg_ids.extend(k.get("belege", []))
        lektion = k.get("lektion")
        k["zustand"] = (
            _zustand(staende.get(lektion), dauern.get(lektion, 0.0)) if lektion else None
        )
        _faerbe(k.get("kinder", []), staende, dauern, beleg_ids)


def _zustand(stand: dict | None, dauer: float) -> str:
    """R-4: der Anzeigezustand aus den zwei Achsen, mit der Schwelle 0,95."""
    if stand is None:
        return "ungehoert"
    if stand["fragen"] == "fertig":
        return "fragen_beantwortet"
    anteil = _anteil(float(stand["position_sek"]), dauer)
    if anteil >= GEHOERT_SCHWELLE:
        return "gehoert"
    if anteil >= 0.02:
        return "angefangen"
    return "ungehoert"


def _nicht_da(code: str, grund: str, **rest: Any):
    return jsonify({"fehler": code, "grund": grund, **rest}), 404


def _falsch(code: str, grund: str, **rest: Any):
    return jsonify({"fehler": code, "grund": grund, **rest}), 400


# Der Anbieter erlaubt 16 384 Token Anweisung. Das Verhaeltnis ist **gemessen**,
# nicht geschaetzt: Die abgelehnte Anweisung vom 12.09.2026 hatte 355 518
# Zeichen und 90 468 Token, also 3,93 Zeichen je Token. Mit 50 000 Zeichen
# fuer das Wissen bleiben rund 3 600 Token Luft fuer Haltung und Gedaechtnis.
ANWEISUNG_ZEICHEN = 50_000


def _wissensblock(zeilen) -> tuple[int, str]:
    """Das Kapitelwissen so ausfuehrlich, wie es in die Anweisung passt.

    Gibt die Stufe zurueck (1 = ganz, 2 = Kurzfassungen, 3 = nur Kernsaetze)
    und den Text. Die Reichweite bleibt auf jeder Stufe vollstaendig; es
    faellt die Tiefe.
    """
    def erster_satz(text: str) -> str:
        """Der erste Satz traegt bei diesen Kurzfassungen die Aussage; der Rest
        ist Bedingung und Einschraenkung. Fuer einen Gegenspieler, der eine
        Frage stellen soll, reicht die Aussage."""
        t = " ".join(text.split())
        for ende in (". ", "; ", " — "):
            stelle = t.find(ende)
            if 40 < stelle < 240:
                return t[:stelle + 1]
        return t[:240]

    def bauen(stufe: int) -> str:
        raus = []
        for z in zeilen:
            kopf = f"\n## {z['id']}"
            if stufe == 4:
                marke = (z["stichwort"] or "").strip()
                raus.append(f"{kopf} {marke + ' — ' if marke else ''}{z['titel']}")
                continue
            raus.append(f"{kopf} — {z['titel']}")
            if z["kurzfassung"]:
                raus.append(z["kurzfassung"].strip() if stufe < 3
                            else erster_satz(z["kurzfassung"]))
            if stufe == 1 and z["inhalt"]:
                raus.append(z["inhalt"].strip())
        return "\n".join(raus)

    for stufe in (1, 2, 3, 4):
        text = bauen(stufe)
        if len(text) <= ANWEISUNG_ZEICHEN or stufe == 4:
            return stufe, text
    return 4, bauen(4)


def _gespraechs_anweisung(db, kapitel_id: str, we_ids: list[str],
                          frueher: "list[dict[str, Any]] | None" = None,
                          *, mit_werkzeugen: bool = True) -> str:
    """Der Sitzungsprompt: Kapitelwissen, Gedaechtnis, Haltung des Gegenspielers.

    Das Wissen kommt mit (OBF-14). Was nicht darin steht, weiss der Partner
    nicht belegt — und muss das sagen (DIS-8, TB-8). Genau daran haengt der
    Unterschied zu einem Chatbot.

    **Es passt aber nicht mehr vollstaendig hinein.** Der Anbieter erlaubt
    16 384 Token Anweisung; K-01 mit 178 Wissenseinheiten braucht 90 468. Der
    Fall war in kapitel/K-01.md vorhergesagt und ist am 12.09.2026
    eingetreten.

    Deshalb wird **gestuft gekuerzt**, und zwar so, dass die Reichweite
    erhalten bleibt und die Tiefe zuerst faellt:

        1. Behauptung + Kurzfassung + Inhalt   (wie bisher)
        2. Behauptung + Kurzfassung
        3. Behauptung + erster Satz der Kurzfassung
        4. Stichwort + Behauptung

    Auf jeder Stufe kennt der Partner **alle** Einheiten des Kapitels; er
    weiss nur weniger ueber jede. Die Umkehrung — wenige Einheiten ganz — waere
    schlimmer: Dann behauptete er, das Kapitel zu kennen, und uebersaehe die
    Haelfte.

    **Er erfaehrt, auf welcher Stufe er steht**, und sagt es (TB-8).

    **Seit dem 14.09.2026 ist die Kuerzung kein Wissensverlust mehr**, sondern
    eine andere Ladereihenfolge: `bibliothek_nachschlagen` holt die Tiefe
    zurueck, die hier faellt, und zwar belegt (DIS-25, `dienst/werkzeuge.py`).
    Vorher stand an dieser Stelle, das sei "bis dahin die ehrliche Naeherung"
    — bis dahin hat gedauert.

    ``frueher`` sind die letzten Sitzungen zu diesem Kapitel. Sie machen aus
    einer Reihe von Einzelgespraechen einen fortgesetzten Austausch: Der
    Partner weiss dann, was schon besprochen und was schon verstanden wurde,
    und faengt nicht bei jedem Neustart von vorn an.
    """
    zeilen = db.execute(
        "SELECT id, titel, stichwort, kurzfassung, inhalt, prueffrage FROM einheiten"
        "  WHERE id IN (%s)" % ",".join("?" * len(we_ids)), we_ids).fetchall()
    kapitel = db.execute(
        "SELECT titel, kurzfassung AS kern FROM kapitel WHERE id = ?", (kapitel_id,)
    ).fetchone()

    stufe, wissen = _wissensblock(zeilen)
    teile = [
        "Du bist ein anspruchsvoller Lern-Gegenspieler zum Kapitel "
        f"„{kapitel['titel'] if kapitel else kapitel_id}".rstrip() + "“.",
        "",
        f"DEIN WISSEN — alle {len(zeilen)} Einheiten des Kapitels, und nur die:",
        wissen,
    ]
    if stufe > 1:
        teile += [
            "",
            "**Du hast zu jeder Einheit nur " + (
                "die Kurzfassung" if stufe == 2 else
                "den Kernsatz und einen Satz dazu" if stufe == 3 else "den Kernsatz")
            + ", nicht den vollen Text.** Das Kapitel ist zu gross fuer eine",
            "Sitzungsanweisung. Wenn eine Frage ins Detail geht, sag das:",
            "„Genauer steht das in der Lektion, hier habe ich nur den Kern.“",
            "Tu nicht so, als haettest du mehr.",
        ]
    if frueher:
        # Auch das Gedaechtnis hat ein Budget: Es darf die Anweisung nicht
        # sprengen, aber es ist das Juengste und damit das Wichtigste — also
        # wird vorn gekuerzt, nicht hinten.
        teile += ["", "WAS IHR SCHON BESPROCHEN HABT:"]
        for sitzung in frueher:
            teile.append("")
            for b in sitzung["beitraege"]:
                wer = "Lernender" if b["rolle"] == "lernender" else "Du"
                teile.append(f"{wer}: {b['text'].strip()}")
        teile += [
            "",
            "Knuepf daran an. Wiederhole nicht, was schon sass — geh tiefer oder",
            "greif auf, was offen blieb. Wenn er dich fragt, worueber ihr gesprochen",
            "habt, sag es. Tu aber nicht so, als erinnertest du dich an mehr als",
            "das hier Stehende.",
        ]

    teile += [
        "",
        "DER LERNENDE WEISS NICHT, WAS „DEIN MATERIAL“ IST. Sag es nie. Kein",
        "„das steht nicht in deinem Material“, kein „in unserem Material steht“.",
        "Er hoert ein Gespraech, keine Datenbankauskunft. Sag stattdessen, was",
        "ueber die Sache stimmt: „Dazu habe ich nichts Belastbares“ oder „das",
        "sehe ich kurz nach“. Der Unterschied ist, worueber der Satz redet —",
        "ueber die Sache oder ueber uns. (Dasselbe gilt fuer die Folgen, POD-18.)",
    ]
    # Werkzeuge nur versprechen, wenn der Browser sie ausfuehren kann. Ein
    # Partner, der ein Werkzeug ankuendigt, das es in dieser Sitzung nicht
    # gibt, ist schlimmer als einer ohne Werkzeuge.
    if mit_werkzeugen:
        teile += [
            "",
            "WAS DU NICHT AUSWENDIG WEISST, KANNST DU HOLEN. Du hast vier Werkzeuge:",
            "- `bibliothek_nachschlagen` — die GANZE Bibliothek, nicht nur dieses",
            "  Kapitel. Millisekunden, kein Wort darueber noetig. Was zurueckkommt,",
            "  ist BELEGT. **Nimm es, bevor du sagst, du wuesstest etwas nicht.**",
            "- `recherchieren` — Websuche, wenn die Bibliothek nichts hergibt.",
            "  Dauert wenige Sekunden: ein kurzes „Moment, ich sehe nach“ genuegt,",
            "  keine lange Ueberbrueckung. Was zurueckkommt, ist UNGEPRUEFT — sag",
            "  ausdruecklich, dass du es frisch nachgesehen hast und es nicht aus",
            "  der Bibliothek stammt.",
            "- `rechercheauftrag_aufnehmen` — Luecke fuer spaeter festhalten. Stumm.",
            "- `punkt_geprueft` — Agenda abhaken. Stumm.",
            "",
            "Die Reihenfolge ist die Rangfolge: erst dein Wissen, dann die",
            "Bibliothek, dann das Netz. Erfinde nie eine Quelle oder eine Zahl.",
            "",
            "**Belegt und Nachgesehenes hoeren sich gleich an, wenn du nicht",
            "aufpasst.** Beides kommt aus deinem Mund. Nur du kannst es",
            "auseinanderhalten, und der Lernende muss es hoeren.",
        ]
    else:
        teile += [
            "",
            "Was du nicht weisst, weisst du nicht. Sag es als Aussage ueber die",
            "Sache („dazu habe ich nichts Belastbares“), nicht ueber uns, und",
            "erfinde nie eine Quelle oder eine Zahl.",
        ]
    teile += [
        "",
        "SO FUEHRST DU DAS GESPRAECH:",
        "- Stelle immer nur EINE Frage auf einmal. Warte die Antwort ab.",
        "- Verrate die Loesung nicht sofort. Lass den Lernenden seine Position verteidigen.",
        "- Widersprich begruendet, wenn etwas falsch oder halb ist, und nenne die Fundstelle.",
        "- Decke Luecken auf, statt sie zu ueberspielen.",
        "- Passe die Schwierigkeit an: sicher geantwortet, dann tiefer; schwimmt er, einen Schritt zurueck.",
        "- Pruefe zwischendurch, ob er verstanden hat, statt weiter zu erklaeren.",
        "- Wo das Material einen Widerspruch enthaelt, loese ihn nicht auf. Trag ihn aus.",
        "",
        "Eroeffne mit einer Frage, nicht mit einer Zusammenfassung.",
    ]
    text = "\n".join(teile)
    if len(text) > ANWEISUNG_ZEICHEN * 1.25:
        # Notbremse: Lieber ohne Gedaechtnis als ohne Gespraech.
        ohne = [t for t in teile if not t.startswith(("Lernender:", "Du:"))]
        text = "\n".join(ohne)
    return text


def main() -> None:  # pragma: no cover
    app = erzeuge_app()
    app.run(host=os.environ.get("TEACHBUDDY_HOST", "127.0.0.1"),
            port=int(os.environ.get("TEACHBUDDY_PORT", "5088")))


if __name__ == "__main__":  # pragma: no cover
    main()
