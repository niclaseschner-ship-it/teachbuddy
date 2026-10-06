"""Der Bau einer Folge — Skript, Probe, Vertonung, Schnitt (AUF-6).

    Wissenseinheiten
      → Skript-Agent (GPT, AUF-16)        skript.md      POD-11
      → Belegprobe (mechanisch, AUF-8b)   probe.md
      → Marker entfernen (AUF-8c)
      → Vertonung je Sprecherzeile        .teile/*.mp3   POD-8
      → Schnitt mit Pausen                folge.mp3      POD-9/10
      → Zeitmarken + Längenprobe          folge.json     POD-3/12

Ein Bau ist ein **Auftrag mit Zustand** (AUF-6): `offen`, `läuft`, `fertig`,
`gescheitert` stehen in `auftrag.json` und werden fortgeschrieben, während
er läuft. Die App fragt ab, statt zu warten.

Die Auftrags-ID ist ein Hash über Titel, Stände der Einheiten, Stimmen und
den Auftragstext. Derselbe Eingang gibt denselben Auftrag (AUF-7); eine
korrigierte Wissenseinheit gibt einen neuen.

Aufruf:

    python3 -m podcast.bauen \\
        --einheiten demo/eingang/M-016/einheiten \\
        --titel "Die drei Verzerrungen des Judges"

Ohne `--echte-vertonung` läuft der ganze Weg über `StilleVertonung` und
kostet nichts.
"""

import argparse
import dataclasses
import datetime
import hashlib
import json
import logging
import os
import re
import shutil
import sys

import pfade

from . import belegprobe as belegprobe_mod
from . import einheiten as einheiten_mod
from . import fassung as fassung_mod
from . import skript as skript_mod
from . import vertonung as vertonung_mod

logger = logging.getLogger(__name__)

STANDARD_ARBEIT = str(pfade.PODCAST_ARBEIT)

# POD-3: Eine Folge entspricht einer Lektion und liegt zwischen fünf und
# zehn Minuten. Der Zuschnitt ist die Zeitspanne, nicht die Zahl der
# Einheiten.
DAUER_MIN_SEK = 300
DAUER_MAX_SEK = 600

# POD-1a: Der Gast trägt den Inhalt. Unterschreitet sein Anteil diese
# Schwelle, ist das Verhältnis nicht mehr „deutlich zugunsten des Gastes",
# sondern ein aufgeteilter Vortrag.
GAST_ANTEIL_MIN = 0.60

ZUSTAENDE = ("offen", "läuft", "fertig", "gescheitert")


class BauFehler(Exception):
    """Der Auftrag ist gescheitert. Die Meldung ist der Grund (AUF-6)."""


@dataclasses.dataclass
class Ergebnis:
    auftrag_id: str
    zustand: str
    verzeichnis: str
    dauer_sek: float = 0.0
    zeichen_vertont: int = 0
    zeichen_neu_vertont: int = 0
    grund: str = ""

    @property
    def audio(self) -> str:
        return os.path.join(self.verzeichnis, "folge.mp3")

    @property
    def manifest(self) -> str:
        return os.path.join(self.verzeichnis, "folge.json")


# --------------------------------------------------------------------------
# Auftragszustand (AUF-6)
# --------------------------------------------------------------------------

def _slug(text: str) -> str:
    text = text.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:48] or "folge"


def auftrag_id(*, titel: str,
               einheiten: list[einheiten_mod.Wissenseinheit],
               stimmen: dict[str, str]) -> str:
    """Deterministisch über alles, was den Bau bestimmt (AUF-7, AUF-9)."""
    with open(skript_mod.AUFTRAG_PFAD, "rb") as f:
        auftrag_hash = hashlib.sha256(f.read()).hexdigest()[:16]
    nutzlast = "\n".join([
        titel.strip(),
        auftrag_hash,
        ",".join("%s=%s" % (k, stimmen[k]) for k in sorted(stimmen)),
        *("%s@%s" % (e.id, e.stand) for e in einheiten),
    ])
    kurz = hashlib.sha256(nutzlast.encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (_slug(titel), kurz)


def _schreibe_zustand(verzeichnis: str, zustand: str, **felder) -> None:
    assert zustand in ZUSTAENDE, zustand
    os.makedirs(verzeichnis, exist_ok=True)
    pfad = os.path.join(verzeichnis, "auftrag.json")
    daten = lies_zustand(verzeichnis) or {}
    daten.update(felder)
    daten["zustand"] = zustand
    daten["zuletzt"] = datetime.datetime.now().isoformat(timespec="seconds")
    tmp = pfad + ".neu"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, indent=2)
    os.replace(tmp, pfad)


def lies_zustand(verzeichnis: str) -> dict | None:
    """Was die App abfragt (AUF-6)."""
    pfad = os.path.join(verzeichnis, "auftrag.json")
    if not os.path.exists(pfad):
        return None
    try:
        with open(pfad, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


# --------------------------------------------------------------------------
# Vertonungs-Cache (geerbt: `.index.json` aus album_builder)
# --------------------------------------------------------------------------

class TeileCache:
    """Hash-Index über Sprechtext, Stimme und Stimmen-Map.

    Geerbt aus dem Hörspiel-Vorbild: Ein Teil wird nur neu
    vertont, wenn sich sein Text, seine Stimme **oder die Stimmen-Map**
    geändert haben. Das spart bei jeder Korrektur an einer Lektion den
    Rest der Folge — und bei echter Vertonung bares Geld.

    Zwei Zusätze gegenüber dem Vorbild: Der Name des Anbieters geht in den
    Hash ein (sonst zieht ein Azure-Lauf die Stille-Teile aus dem Cache),
    und die **gemessene Dauer** wird mitgelegt (sonst müsste jeder Lauf
    jeden Teil neu durch ffprobe schicken).
    """

    def __init__(self, wurzel: str):
        self.wurzel = wurzel
        self.index_pfad = os.path.join(wurzel, ".index.json")
        os.makedirs(wurzel, exist_ok=True)
        self.index: dict[str, dict] = {}
        if os.path.exists(self.index_pfad):
            try:
                with open(self.index_pfad, encoding="utf-8") as f:
                    self.index = json.load(f)
            except (OSError, ValueError):
                self.index = {}
        self.treffer = 0
        self.neu = 0

    @staticmethod
    def schluessel(*, text: str, voice: str, stimmen: dict[str, str],
                   anbieter: str) -> str:
        """Alles, was den Klang bestimmt, geht in den Schlüssel.

        **Auch das Sprechtempo.** Fehlt es, liefert der Cache nach einer
        Tempoänderung die alten Dateien zurück und die Änderung wirkt nicht —
        genau der Fehler, vor dem das Hörspiel-Vorbild warnt
        („voices-Map in den Hash aufnehmen, sonst rebuildet eine
        Voice-Änderung nicht"). Am 11.09.2026 ist er hier einmal aufgetreten.
        """
        nutzlast = "\n".join([
            text.strip(), voice.strip().lower(), anbieter,
            ",".join("%s=%s" % (k, stimmen[k]) for k in sorted(stimmen)),
            "tempo=%.3f" % vertonung_mod.SPRECHTEMPO,
        ])
        return hashlib.sha256(nutzlast.encode("utf-8")).hexdigest()[:16]

    def hole(self, schluessel: str) -> tuple[bytes, float] | None:
        eintrag = self.index.get(schluessel)
        if not eintrag:
            return None
        pfad = os.path.join(self.wurzel, eintrag["datei"])
        if not os.path.exists(pfad):
            return None
        with open(pfad, "rb") as f:
            self.treffer += 1
            return f.read(), float(eintrag["dauer_sek"])

    def lege_ab(self, schluessel: str, mp3: bytes, dauer: float) -> None:
        name = schluessel + ".mp3"
        pfad = os.path.join(self.wurzel, name)
        tmp = pfad + ".neu"
        with open(tmp, "wb") as f:
            f.write(mp3)
        os.replace(tmp, pfad)
        self.index[schluessel] = {"datei": name, "dauer_sek": round(dauer, 3)}
        self.neu += 1
        tmp = self.index_pfad + ".neu"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.index, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.index_pfad)


# --------------------------------------------------------------------------
# Die Proben, die nicht die Belegprobe sind
# --------------------------------------------------------------------------

def pruefe_sprechanteil(skript: skript_mod.Skript) -> None:
    """POD-1a — die Rollen sind ungleich verteilt."""
    anteile = skript.sprechanteile()
    fremde = set(anteile) - set(vertonung_mod.STIMMEN)
    if fremde:
        raise BauFehler(
            "Skript enthält Sprecher ohne Stimme: %s (POD-1 kennt nur "
            "MODERATOR und GAST)" % ", ".join(sorted(fremde)))
    gast = anteile.get("GAST", 0.0)
    if gast < GAST_ANTEIL_MIN:
        raise BauFehler(
            "Der Gast hat nur %.0f %% des gesprochenen Textes (verlangt sind "
            "mindestens %.0f %%). Zwei gleich viel erklärende Stimmen sind "
            "kein Gespräch, sondern ein aufgeteilter Vortrag (POD-1a)."
            % (gast * 100, GAST_ANTEIL_MIN * 100))


def pruefe_laenge(dauer_sek: float) -> None:
    """POD-3 — fünf bis zehn Minuten, sonst neu schneiden."""
    if dauer_sek < DAUER_MIN_SEK:
        raise BauFehler(
            "Folge dauert %s, Mindestmaß sind %s (POD-3). Das Material trägt "
            "keine eigene Folge — mit der nächsten Lektion zusammenlegen."
            % (_mmss(dauer_sek), _mmss(DAUER_MIN_SEK)))
    if dauer_sek > DAUER_MAX_SEK:
        raise BauFehler(
            "Folge dauert %s, Höchstmaß sind %s (POD-3). Zu viel Material für "
            "eine Folge — teilen." % (_mmss(dauer_sek), _mmss(DAUER_MAX_SEK)))


def _mmss(sek: float) -> str:
    return "%d:%02d min" % (int(sek) // 60, int(sek) % 60)


# --------------------------------------------------------------------------
# Der Bau
# --------------------------------------------------------------------------

def baue(*, einheiten_pfad: str, titel: str,
         arbeit: str = STANDARD_ARBEIT,
         tts=None,
         skript_datei: str | None = None,
         neues_skript: bool = False,
         nur: "list[str] | None" = None,
         stimmen: dict[str, str] | None = None) -> Ergebnis:
    """Baut eine Folge und gibt ihren Auftragszustand zurück.

    `tts=None` → `StilleVertonung`: der ganze Weg, kostenlos.
    `skript_datei` → ein fertiges Skript statt eines Agentenaufrufs; damit
    ist die Pipeline ohne GPT prüfbar.
    """
    stimmen = stimmen or dict(vertonung_mod.STIMMEN)
    einheiten = einheiten_mod.lies_verzeichnis(einheiten_pfad, nur=nur)
    a_id = auftrag_id(titel=titel, einheiten=einheiten, stimmen=stimmen)
    verzeichnis = os.path.join(arbeit, a_id)
    os.makedirs(verzeichnis, exist_ok=True)
    bau = os.path.join(verzeichnis, ".bau")
    shutil.rmtree(bau, ignore_errors=True)   # AUF-7: kein Rest vom Fehlschlag
    os.makedirs(bau)

    tts = tts or vertonung_mod.StilleVertonung(bau)
    _schreibe_zustand(
        verzeichnis, "läuft", id=a_id, titel=titel, format="podcast",
        einheiten=[{"id": e.id, "stand": e.stand} for e in einheiten],
        stimmen=stimmen, anbieter_vertonung=tts.name,
        begonnen=datetime.datetime.now().isoformat(timespec="seconds"),
    )

    try:
        ergebnis = _baue_innen(
            einheiten=einheiten, titel=titel, a_id=a_id,
            verzeichnis=verzeichnis, bau=bau, arbeit=arbeit, tts=tts,
            skript_datei=skript_datei, neues_skript=neues_skript,
            stimmen=stimmen)
    except (BauFehler, skript_mod.SkriptFehler, skript_mod.Ablehnung,
            skript_mod.AgentFehler, vertonung_mod.TTSFehler,
            vertonung_mod.SchnittFehler, einheiten_mod.EinheitFehler) as exc:
        grund = "%s: %s" % (type(exc).__name__, exc)
        _schreibe_zustand(verzeichnis, "gescheitert", grund=grund)
        shutil.rmtree(bau, ignore_errors=True)
        return Ergebnis(auftrag_id=a_id, zustand="gescheitert",
                        verzeichnis=verzeichnis, grund=grund)
    finally:
        shutil.rmtree(bau, ignore_errors=True)
    return ergebnis


def _baue_innen(*, einheiten, titel, a_id, verzeichnis, bau, arbeit, tts,
                skript_datei, neues_skript, stimmen) -> Ergebnis:
    # --- Skript (POD-11) ---------------------------------------------------
    skript_pfad = os.path.join(verzeichnis, "skript.md")
    modell = "—"
    if skript_datei:
        with open(skript_datei, encoding="utf-8") as f:
            roh = f.read()
        modell = "aus Datei %s" % os.path.basename(skript_datei)
        with open(skript_pfad, "w", encoding="utf-8") as f:
            f.write(roh)
    elif os.path.exists(skript_pfad) and not neues_skript:
        # AUF-7: Ein Wiederholungslauf nach einem Fehlschlag in der
        # Vertonung würfelt das Skript nicht neu.
        with open(skript_pfad, encoding="utf-8") as f:
            roh = f.read()
        modell = (lies_zustand(verzeichnis) or {}).get("modell_skript", "—")
        logger.info("Skript aus vorherigem Lauf übernommen (%s)", skript_pfad)
    else:
        material = skript_mod.baue_material(einheiten, thema=titel)
        roh, modell = skript_mod.rufe_agenten(
            material=material, thema=titel, arbeit=verzeichnis)

    skript = skript_mod.lies(roh)
    _schreibe_zustand(verzeichnis, "läuft", modell_skript=modell)

    # AUF-18a: Eine Fassungsnummer, die nicht mehr zum Auftragstext passt,
    # ist schlimmer als keine — sie behauptet etwas Falsches ueber die Folge.
    drift = fassung_mod.pruefe_stand()
    if drift:
        logger.warning("Fassung und Auftragstext gehen auseinander: %s", drift)

    # --- Belegprobe (AUF-8b) ----------------------------------------------
    probe = belegprobe_mod.pruefe(skript, einheiten)
    with open(os.path.join(verzeichnis, "probe.md"), "w",
              encoding="utf-8") as f:
        f.write(probe.bericht())
    if not probe.bestanden:
        raise BauFehler(
            "Belegprobe gescheitert, %d Befunde — siehe %s\n  %s"
            % (len(probe.befunde), os.path.join(verzeichnis, "probe.md"),
               "\n  ".join(str(b) for b in probe.befunde[:8])))

    pruefe_sprechanteil(skript)

    # --- Vertonung je Sprecherzeile (POD-8, AUF-8c) ------------------------
    cache = TeileCache(os.path.join(arbeit, ".teile"))
    teile: list[vertonung_mod.Teil] = []
    kapitelmarken: list[dict] = []
    laufzeit = 0.0
    zeichen_vertont = 0

    for abschnitt in skript.abschnitte:
        kapitelmarken.append({
            "sek": int(round(laufzeit)),
            "titel": abschnitt.titel,
            "art": abschnitt.art,
        })
        for i, zeile in enumerate(abschnitt.zeilen):
            # AUF-8c: Marker raus, bevor irgendetwas den Text zu sehen kriegt.
            text = zeile.sprechtext
            if not text:
                raise BauFehler(
                    "Zeile %d (%s) besteht nur aus Markern"
                    % (zeile.zeilennummer, zeile.sprecher))
            voice = stimmen[zeile.sprecher]
            zeichen_vertont += len(text)

            schluessel = cache.schluessel(
                text=text, voice=voice, stimmen=stimmen, anbieter=tts.name)
            getroffen = cache.hole(schluessel)
            if getroffen:
                mp3, dauer = getroffen
            else:
                mp3 = tts.synthese(text=text, voice=voice)
                dauer = vertonung_mod.dauer_sek(mp3, arbeit=bau)
                cache.lege_ab(schluessel, mp3, dauer)

            letzte_im_abschnitt = (i == len(abschnitt.zeilen) - 1)
            pause = (vertonung_mod.PAUSE_ABSCHNITT_SEK if letzte_im_abschnitt
                     else vertonung_mod.PAUSE_ZEILE_SEK)
            teile.append(vertonung_mod.Teil(mp3=mp3, pause_sek=pause))
            laufzeit += dauer + pause

    if teile:
        teile[-1].pause_sek = 0.0  # kein Nachklang am Ende der Folge

    logger.info("Vertonung: %d Teile, %d aus dem Cache, %d neu",
                len(teile), cache.treffer, cache.neu)

    # --- Schnitt (POD-9/10) ------------------------------------------------
    audio_bau = os.path.join(bau, "folge.mp3")
    vertonung_mod.fuege_zusammen(teile, audio_bau, arbeit=bau)
    dauer = vertonung_mod.dauer_sek(audio_bau, arbeit=bau)

    # --- Längenprobe (POD-3) -----------------------------------------------
    pruefe_laenge(dauer)

    # --- Hülle (AUF-9, AUF-11, AUF-12, POD-7a, POD-12) ---------------------
    quellen = sorted({b.split("-")[1] for b in probe.belege_verwendet})
    manifest = {
        "id": a_id,
        "format": "podcast",
        "titel": skript.titel,
        "auftrag_titel": titel,
        "zustand": "fertig",
        "erzeugt_am": datetime.datetime.now().isoformat(timespec="seconds"),
        "dauer_sek": int(round(dauer)),
        "audio": "folge.mp3",
        "skript": "skript.md",
        "kapitelmarken": kapitelmarken,
        "stimmen": stimmen,
        "sprechanteile": {s: round(a, 3)
                          for s, a in skript.sprechanteile().items()},
        # POD-7a / E-21b: zwei verschiedene Zahlen, beide gemessen.
        # `zeichen_vertont` ist, was die Folge kostet, wenn man sie von
        # Null baut — das ist die Zahl für die Lernpfad-Bilanz (E-21d).
        # `zeichen_neu_vertont` ist, was dieser Lauf tatsächlich an den
        # Anbieter geschickt hat; bei vollem Cache-Treffer null. Wer die
        # erste für die zweite hält, rechnet jeden Wiederholungslauf noch
        # einmal in Rechnung.
        "zeichen_vertont": zeichen_vertont,
        "zeichen_neu_vertont": getattr(tts, "zeichen", 0),
        "anbieter_vertonung": tts.name,
        "modell_skript": modell,
        # AUF-18a: Welche Fassung der Pipeline diese Folge gebaut hat. Ohne das
        # ist nach zwei Nachbesserungen nicht mehr zu sagen, was in einer
        # fertigen Folge steckt — und eine Rueckmeldung dazu nicht zu deuten.
        "pipeline": fassung_mod.als_fracht(),
        "einheiten": [{"id": e.id, "stand": e.stand, "titel": e.titel}
                      for e in einheiten],
        "einheiten_verwendet": list(probe.einheiten_verwendet),
        "einheiten_ungenutzt": list(probe.einheiten_ungenutzt),
        "belege_verwendet": list(probe.belege_verwendet),
        "quellen": quellen,
    }
    with open(os.path.join(bau, "folge.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    # AUF-7: erst wenn alles steht, wandert es an seinen Platz.
    for name in ("folge.mp3", "folge.json"):
        os.replace(os.path.join(bau, name), os.path.join(verzeichnis, name))

    _schreibe_zustand(
        verzeichnis, "fertig", dauer_sek=int(round(dauer)),
        zeichen_vertont=zeichen_vertont,
        zeichen_neu_vertont=getattr(tts, "zeichen", 0),
        modell_skript=modell, kapitelmarken=len(kapitelmarken))
    return Ergebnis(auftrag_id=a_id, zustand="fertig", verzeichnis=verzeichnis,
                    dauer_sek=dauer, zeichen_vertont=zeichen_vertont,
                    zeichen_neu_vertont=getattr(tts, "zeichen", 0))


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="podcast.bauen",
        description="Baut eine Podcast-Folge aus Wissenseinheiten (POD).")
    p.add_argument("--einheiten", required=True,
                   help="Verzeichnis mit den Wissenseinheiten (*.md)")
    p.add_argument("--titel", required=True, help="Titel/Thema der Folge")
    p.add_argument("--nur", default=None,
                   help="Zuschnitt der Lektion, z. B. WE-0001,WE-0002 (POD-3)")
    p.add_argument("--arbeit", default=STANDARD_ARBEIT,
                   help="Arbeitsverzeichnis (Standard: arbeit/podcast)")
    p.add_argument("--skript", default=None,
                   help="fertiges Skript statt eines Agentenaufrufs")
    p.add_argument("--neues-skript", action="store_true",
                   help="Skript neu erzeugen, auch wenn eines vorliegt")
    p.add_argument("--echte-vertonung", action="store_true",
                   help="Azure statt Stille — kostet Geld je Zeichen (POD-7a)")
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    tts = None
    if args.echte_vertonung:
        try:
            tts = vertonung_mod.aus_umgebung()
        except vertonung_mod.TTSFehler as exc:
            print("FEHLER: %s" % exc, file=sys.stderr)
            return 2
        print("Echte Vertonung über Azure — das kostet Geld je Zeichen.")

    ergebnis = baue(einheiten_pfad=args.einheiten, titel=args.titel,
                    arbeit=args.arbeit, tts=tts, skript_datei=args.skript,
                    neues_skript=args.neues_skript,
                    nur=[s.strip() for s in args.nur.split(",")] if args.nur
                    else None)

    print()
    print("Auftrag %s: %s" % (ergebnis.auftrag_id, ergebnis.zustand))
    print("  %s" % ergebnis.verzeichnis)
    if ergebnis.zustand == "fertig":
        print("  Dauer:    %s" % _mmss(ergebnis.dauer_sek))
        print("  Zeichen:  %d in der Folge, %d in diesem Lauf neu vertont"
              % (ergebnis.zeichen_vertont, ergebnis.zeichen_neu_vertont))
        return 0
    print("  Grund:    %s" % ergebnis.grund)
    return 1


if __name__ == "__main__":
    sys.exit(main())
