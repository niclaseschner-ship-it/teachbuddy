"""Vertonung — Text zu MP3, Pausen, Zusammenfügen (POD-6/7/8/9).

Der Azure-Adapter stammt aus einem früheren Hörspiel-Projekt desselben Autors,
Schnittstelle unverändert: `synthese(text=, voice=) → mp3-bytes`. Zwei
Dinge sind anders:

  - **Eigene Umgebungsvariablen** (`TEACHBUDDY_AZURE_*`, E-11a). Damit
    bleiben die Kosten trennbar und eine Nutzungsgrenze im einen Projekt
    legt das andere nicht still.
  - **`StilleVertonung` ist der Standard.** Der ganze Weg — Skript,
    Belegprobe, Schnitt, Zeitmarken, Längenprobe — muss ohne einen Cent
    Vertonungskosten durchlaufen. Echtes Azure nur auf ausdrückliches Flag.

Das ffmpeg-Zusammenfügen ist ebenfalls geerbt, samt der Erfahrung, die man
sonst teuer selbst macht:

    Re-encode mit libmp3lame bei jedem Concat-Schritt — sonst DTS-Müll.

Abweichung vom Vorbild: **kein System-Temp.** Auf kleinen Geräten ist `/tmp`
oft ein RAM-Dateisystem, und jedes MP3 dort frisst Arbeitsspeicher (APP-11). Alle
Funktionen hier verlangen deshalb ein Arbeitsverzeichnis.
"""

import dataclasses
import logging
import os
import re
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# POD-7, entschieden 11.09.2026: die fragende Stimme heller, die erklärende
# tiefer. Tauschbar nach einer Hörprobe, dann aber für den ganzen Lernpfad
# (POD-7b).
STIMMEN = {"MODERATOR": "shimmer", "GAST": "onyx"}

# POD-9, geerbt aus dem Hörspiel-Vorbild.
# Rückmeldung vom 11.09.2026: "wir hatten auf Kinderhörbuch optimiert, es darf schneller
# sein". Die geerbten Werte stammen aus dem Hörspiel-Vorbild, wo Pausen dem Kind
# Zeit zum Mitgehen geben. Ein Lern-Podcast für Erwachsene darf straffer sein.
PAUSE_ZEILE_SEK = float(os.environ.get("TEACHBUDDY_PAUSE_ZEILE", "0.35"))
PAUSE_ABSCHNITT_SEK = float(os.environ.get("TEACHBUDDY_PAUSE_ABSCHNITT", "1.0"))

# Sprechtempo der Synthese selbst. Azure nimmt 0.25 bis 4.0.
#
# Das ist der bessere Hebel als der Abspieler: Azure passt die Betonung an,
# während ein beschleunigter Abspieler nur schneller abspielt. Beim Testhören klang die
# erste Folge auf 1,25 und fand es passend — davon geht ein Teil ins
# Grundtempo, damit 1,0 im Abspieler schon angenehm ist und der Regler nach
# oben Luft behält.
SPRECHTEMPO = float(os.environ.get("TEACHBUDDY_SPRECHTEMPO", "1.15"))

# HSP-7/14: grobe Dauerabschätzung, ~150 Wörter je Minute.
WOERTER_PRO_SEKUNDE = 2.5

MP3_ARGS = ["-c:a", "libmp3lame", "-b:a", "96k"]
ANULLSRC = "anullsrc=r=24000:cl=mono"


class TTSFehler(Exception):
    """Die Sprachausgabe ist nicht erreichbar oder antwortet fehlerhaft."""


class SchnittFehler(Exception):
    """ffmpeg hat nicht geliefert — ohne Audio gibt es keine Folge."""


def woerter(text: str) -> int:
    return len([w for w in re.split(r"\s+", text.strip()) if w])


# --------------------------------------------------------------------------
# Die beiden Stimmen-Anbieter
# --------------------------------------------------------------------------

class StilleVertonung:
    """Der Standard: erzeugt Stille in der Länge, die der Text dauern würde.

    Das ist kein Platzhalter zum Wegwerfen, sondern das Werkzeug, mit dem
    der ganze Pfad geprüft wird. Weil die Stille die geschätzte Sprechdauer
    hat, sind Zeitmarken und Längenprobe im Trockenlauf aussagekräftig —
    eine Folge, die mit `StilleVertonung` vier Minuten misst, ist auch mit
    Azure zu kurz.
    """

    name = "stille"

    def __init__(self, arbeit: str):
        self.arbeit = arbeit
        self.zeichen = 0

    def synthese(self, *, text: str, voice: str) -> bytes:
        self.zeichen += len(text)
        sek = max(0.4, woerter(text) / WOERTER_PRO_SEKUNDE)
        return stille_mp3(sek, arbeit=self.arbeit)


class AzureVertonung:
    """Azure-OpenAI-TTS, Schnittstelle wie im Hörspiel-Vorbild (POD-6).

    Kostet Geld je Zeichen (POD-7a) — deshalb zählt der Adapter mit, was
    er tatsächlich geschickt hat, und deshalb steht er nie im Standardweg.
    """

    name = "azure"

    def __init__(self, *, endpoint: str, api_key: str, deployment: str,
                 api_version: str = "2024-10-01-preview"):
        # Lazy-Import: das openai-SDK ist zur Laufzeit optional, die Tests
        # fassen diese Klasse nicht an.
        from openai import AzureOpenAI
        self._client = AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=api_version)
        self._deployment = deployment
        self.zeichen = 0

    def synthese(self, *, text: str, voice: str) -> bytes:
        try:
            antwort = self._client.audio.speech.create(
                model=self._deployment, voice=voice, input=text,
                response_format="mp3", speed=SPRECHTEMPO)
        except Exception as exc:
            logger.warning("Azure TTS nicht erreichbar: %s", exc)
            raise TTSFehler(str(exc)) from exc
        self.zeichen += len(text)
        return antwort.read()


def aus_umgebung() -> AzureVertonung:
    """Baut den Azure-Adapter aus den `TEACHBUDDY_AZURE_*`-Variablen (`zugang.py`)."""
    import sys
    wurzel = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if wurzel not in sys.path:
        sys.path.insert(0, wurzel)
    import zugang

    try:
        endpoint = zugang.hole("azure_endpoint")
        api_key = zugang.hole("azure_key")
        deployment = zugang.hole("azure_deployment")
    except zugang.ZugangFehlt as e:
        raise TTSFehler(
            "%s — ohne diese Zugangsdaten läuft der Bau mit StilleVertonung. "
            "Setze sie in .env (Vorlage: .env.example)." % e) from e

    return AzureVertonung(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=os.environ.get("TEACHBUDDY_AZURE_API_VERSION",
                                   "2024-10-01-preview"),
    )


# --------------------------------------------------------------------------
# Schnitt
# --------------------------------------------------------------------------

def _ffmpeg(args: list[str]) -> None:
    try:
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
                       + args, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise SchnittFehler("ffmpeg nicht gefunden") from exc
    except subprocess.CalledProcessError as exc:
        raise SchnittFehler(
            "ffmpeg: %s" % (exc.stderr or b"").decode("utf-8", "replace")[:400]
        ) from exc


def stille_mp3(sek: float, *, arbeit: str) -> bytes:
    """`sek` Sekunden Stille als MP3."""
    os.makedirs(arbeit, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="stille_", dir=arbeit) as tmp:
        ziel = os.path.join(tmp, "stille.mp3")
        _ffmpeg(["-f", "lavfi", "-i", ANULLSRC, "-t", "%.3f" % sek]
                + MP3_ARGS + [ziel])
        with open(ziel, "rb") as f:
            return f.read()


@dataclasses.dataclass
class Teil:
    """Ein vertontes Stück samt der Pause, die dahinter liegt."""
    mp3: bytes
    pause_sek: float


def fuege_zusammen(teile: list[Teil], ziel: str, *, arbeit: str) -> None:
    """Fügt Teile mit Pausen zu einer MP3 zusammen (POD-8, POD-9).

    Geerbt aus `_concat_chunks_mit_pausen`: ein einziger ffmpeg-Aufruf über
    eine concat-Liste, **mit Re-encode über libmp3lame**. Nativ konkatenierte
    MP3-Streams erzeugen DTS-Müll (Befund im Hörspiel-Vorbild).

    Anders als im Vorbild wird hier **nicht** stillschweigend degradiert:
    Das Hörspiel-Vorbild hängt bei ffmpeg-Fehlern die Bytes ohne Pausen
    aneinander und macht weiter. Für den Podcast wäre das eine Folge, deren
    Zeitmarken auf ein Audio zeigen, das anders klingt als gemessen — der
    Auftrag scheitert lieber (AUF-6).
    """
    if not teile:
        raise SchnittFehler("Keine Teile zum Zusammenfügen")
    os.makedirs(arbeit, exist_ok=True)
    os.makedirs(os.path.dirname(os.path.abspath(ziel)), exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="concat_", dir=arbeit) as tmp:
        eintraege: list[str] = []
        stille_pfade: dict[float, str] = {}
        for i, teil in enumerate(teile):
            pfad = os.path.join(tmp, "t%04d.mp3" % i)
            with open(pfad, "wb") as f:
                f.write(teil.mp3)
            eintraege.append(pfad)
            if teil.pause_sek > 0:
                if teil.pause_sek not in stille_pfade:
                    sp = os.path.join(tmp, "sil_%.2f.mp3" % teil.pause_sek)
                    _ffmpeg(["-f", "lavfi", "-i", ANULLSRC,
                             "-t", "%.3f" % teil.pause_sek] + MP3_ARGS + [sp])
                    stille_pfade[teil.pause_sek] = sp
                eintraege.append(stille_pfade[teil.pause_sek])

        liste = os.path.join(tmp, "liste.txt")
        with open(liste, "w", encoding="utf-8") as f:
            for pfad in eintraege:
                f.write("file '%s'\n" % pfad)
        roh = os.path.join(tmp, "folge.mp3")
        _ffmpeg(["-f", "concat", "-safe", "0", "-i", liste]
                + MP3_ARGS + [roh])
        os.replace(roh, ziel)


def dauer_sek(mp3: bytes | str, *, arbeit: str) -> float:
    """Misst die Dauer einer MP3 mit ffprobe.

    Gemessen statt geschätzt: Die Zeitmarken zeigen dem Hörer, wo ein
    Abschnitt anfängt (POD-12). Eine Schätzung über die Wortzahl wäre über
    zehn Minuten um mehr daneben, als die Marke wert ist.
    """
    if isinstance(mp3, bytes):
        os.makedirs(arbeit, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="probe_", dir=arbeit) as tmp:
            pfad = os.path.join(tmp, "m.mp3")
            with open(pfad, "wb") as f:
                f.write(mp3)
            return dauer_sek(pfad, arbeit=arbeit)
    try:
        lauf = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", mp3],
            check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        raise SchnittFehler("ffprobe: %s" % exc) from exc
    return float(lauf.stdout.strip())
