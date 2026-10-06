"""Das Sprechskript — bauen, holen, lesen (POD-1, POD-11, AUF-16).

Drei Dinge stehen hier, und sie hängen an derselben Form:

  `baue_material` / `rufe_agenten`  — den Auftrag an GPT geben
  `lies`                            — das Ergebnis in Abschnitte und
                                      Sprecherzeilen zerlegen
  `ohne_marker`                     — die Marker vor der Vertonung
                                      entfernen (AUF-8c)

Die Form selbst steht in `auftrag.md` und wird hier geprüft. Wer eine der
beiden Seiten ändert, ändert beide.

Der Sprecher-Präfix und sein Regex sind aus dem Hörspiel-Vorbild
übernommen: Es hatte Mehrstimmigkeit gebaut und
nie benutzt; der Podcast ist ihr erster Anwendungsfall.
"""

import dataclasses
import os
import re
import shutil
import subprocess

from . import einheiten as einheiten_mod

AUFTRAG_PFAD = os.path.join(os.path.dirname(__file__), "auftrag.md")

# T1621, geerbt: "MODERATOR: Wie misst man das?" → voices["MODERATOR"]
PREFIX_RE = re.compile(r"^([A-ZÄÖÜ][A-ZÄÖÜ ]*?):\s*", re.UNICODE)

# AUF-8a: `[B-nnnn-nn]` für eine belegte Aussage, `[E]` für eine Einordnung.
MARKER_RE = re.compile(r"\[\s*(E|B-\d{4}-\d{2})\s*\]")
# Alles in eckigen Klammern — auch das, was kein gültiger Marker ist. Ein
# `[B-17]` oder `[Quelle 3]` ist kein Schreibfehler, sondern genau das,
# wonach die Belegprobe sucht.
KLAMMER_RE = re.compile(r"\[[^\]\n]*\]")

ART_EINLEITUNG = "einleitung"
ART_INHALT = "inhalt"
ART_ZUSAMMENFASSUNG = "zusammenfassung"

# Wo die Codex-CLI liegt: `TEACHBUDDY_CODEX`, sonst `codex` im PATH, sonst die
# Fassung, die die VS-Code-Erweiterung mitbringt.
CODEX_GLOB = os.path.expanduser(
    "~/.vscode-server/extensions/openai.chatgpt-*/bin/*/codex")


class SkriptFehler(Exception):
    """Das Skript hat nicht die Form, die `auftrag.md` verlangt."""


class Ablehnung(Exception):
    """Der Agent hat abgelehnt (AUF-14) — das Material trägt keine Folge."""


class AgentFehler(Exception):
    """Der Skript-Agent war nicht erreichbar oder lieferte nichts (AUF-20)."""


@dataclasses.dataclass(frozen=True)
class Sprecherzeile:
    sprecher: str
    text: str           # mit Markern, so wie im Skript
    zeilennummer: int   # 1-basiert, für Befunde der Belegprobe

    @property
    def marker(self) -> tuple[str, ...]:
        return tuple(m.group(1) for m in MARKER_RE.finditer(self.text))

    @property
    def belege(self) -> tuple[str, ...]:
        return tuple(m for m in self.marker if m != "E")

    @property
    def sprechtext(self) -> str:
        """Was die Sprachausgabe bekommt — ohne Marker (AUF-8c)."""
        return ohne_marker(self.text)


@dataclasses.dataclass(frozen=True)
class Abschnitt:
    titel: str
    art: str
    zeilen: tuple[Sprecherzeile, ...]


@dataclasses.dataclass(frozen=True)
class Skript:
    titel: str
    abschnitte: tuple[Abschnitt, ...]

    @property
    def zeilen(self) -> tuple[Sprecherzeile, ...]:
        return tuple(z for a in self.abschnitte for z in a.zeilen)

    @property
    def zeichen_sprechtext(self) -> int:
        """Was die Vertonung kosten wird (POD-7a)."""
        return sum(len(z.sprechtext) for z in self.zeilen)

    def sprechanteile(self) -> dict[str, float]:
        """Anteil je Sprecher an den gesprochenen Zeichen (POD-1a)."""
        je_sprecher: dict[str, int] = {}
        for zeile in self.zeilen:
            je_sprecher[zeile.sprecher] = (
                je_sprecher.get(zeile.sprecher, 0) + len(zeile.sprechtext))
        gesamt = sum(je_sprecher.values()) or 1
        return {s: n / gesamt for s, n in sorted(je_sprecher.items())}


def ohne_marker(text: str) -> str:
    """Entfernt Beleg-Marker aus einem Text (AUF-8c).

    **Die eine Stelle, an der der geerbte Pfad erweitert werden muss.** Der
    Das Hörspiel-Vorbild kennt das Problem nicht, weil es dort keine Belege gibt.
    Ohne diese Funktion liest Azure „B 0002 01" mitten im Satz vor.

    Entfernt wird nur, was ein *gültiger* Marker ist. Ein `[B-17]` bleibt
    stehen — es soll die Belegprobe scheitern lassen und nicht stillschweigend
    verschwinden.
    """
    text = MARKER_RE.sub("", text)
    # Zurückbleibende doppelte Leerzeichen und Leerzeichen vor Satzzeichen
    # wegräumen: "Erklärung.  " oder "Wort , Wort".
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


# --------------------------------------------------------------------------
# Lesen
# --------------------------------------------------------------------------

def lies(roh: str) -> Skript:
    """Zerlegt ein Skript in Abschnitte und Sprecherzeilen.

    Die `art` eines Abschnitts wird aus seiner Stellung abgeleitet, nicht
    vom Agenten erfragt: Der erste Abschnitt ist die Eröffnung, der letzte
    die Zusammenfassung, der Rest Inhalt. Damit ist POD-4 (Gliederung ist
    hörbar) und POD-1b geprüft statt behauptet — ein Skript ohne Eröffnung
    und Zusammenfassung hat schlicht zu wenige Abschnitte.

    Eine über mehrere Zeilen umbrochene Sprecherzeile wird zu **einer**
    Sprecherzeile zusammengezogen: Sinnabschnitt ist der Redebeitrag
    (POD-10a), nicht der Zeilenumbruch im Editor.
    """
    if roh.lstrip().startswith("# ABLEHNUNG"):
        raise Ablehnung(roh.split("\n", 1)[-1].strip() or "(ohne Begründung)")

    titel = ""
    # (titel, [(zeilennummer, sprecher, textteile)])
    abschnitte: list[tuple[str, list[list]]] = []
    offen: list | None = None  # die gerade laufende Sprecherzeile

    for nr, zeile in enumerate(roh.splitlines(), start=1):
        blank = not zeile.strip()
        if blank:
            offen = None
            continue

        if zeile.startswith("## "):
            abschnitte.append((zeile[3:].strip(), []))
            offen = None
            continue
        if zeile.startswith("# "):
            if not titel:
                titel = zeile[2:].strip()
            offen = None
            continue

        treffer = PREFIX_RE.match(zeile)
        if treffer:
            if not abschnitte:
                raise SkriptFehler(
                    "Zeile %d: Sprecherzeile vor dem ersten `## Abschnitt`" % nr)
            offen = [nr, treffer.group(1), [zeile[treffer.end():].strip()]]
            abschnitte[-1][1].append(offen)
            continue

        if offen is not None:
            offen[2].append(zeile.strip())  # Umbruch derselben Sprecherzeile
            continue

        raise SkriptFehler(
            "Zeile %d: weder Überschrift noch Sprecherzeile: %r"
            % (nr, zeile.strip()[:60]))

    if not titel:
        raise SkriptFehler("Kein `# Titel` am Anfang des Skripts")
    abschnitte = [(t, z) for t, z in abschnitte if z]
    if len(abschnitte) < 3:
        raise SkriptFehler(
            "Nur %d Abschnitte mit Text — POD-4 verlangt Eröffnung, Inhalt "
            "und Zusammenfassung" % len(abschnitte))

    letzter = len(abschnitte) - 1
    gebaut = []
    for i, (a_titel, rohzeilen) in enumerate(abschnitte):
        art = (ART_EINLEITUNG if i == 0
               else ART_ZUSAMMENFASSUNG if i == letzter
               else ART_INHALT)
        gebaut.append(Abschnitt(
            titel=a_titel, art=art,
            zeilen=tuple(
                Sprecherzeile(sprecher=s, text=" ".join(teile).strip(),
                              zeilennummer=nr)
                for nr, s, teile in rohzeilen),
        ))
    return Skript(titel=titel, abschnitte=tuple(gebaut))


# --------------------------------------------------------------------------
# Den Agenten rufen
# --------------------------------------------------------------------------

def baue_material(einheiten: list[einheiten_mod.Wissenseinheit], *,
                  thema: str) -> str:
    """Das Eingabematerial für den Skript-Agenten (AUF-2, AUF-4).

    Die Einheiten gehen im Volltext hinein — mitsamt ihren Markern. Der
    Agent soll sie abschreiben können, statt sie sich auszudenken.
    """
    teile = [
        "# Material für die Folge: %s" % thema,
        "",
        "%d Wissenseinheiten. Mehr hast du nicht." % len(einheiten),
        "",
    ]
    for einheit in einheiten:
        teile += [
            "---",
            "",
            "## %s — %s" % (einheit.id, einheit.titel),
            "",
            "*Grad:* %s · *Belege:* %s"
            % (einheit.grad or "—", ", ".join(einheit.belege)),
            "",
            einheit.inhalt,
            "",
        ]
    return "\n".join(teile)


def finde_codex() -> str:
    """Findet die Codex-CLI (siehe ``CODEX_GLOB``)."""
    import glob
    if os.environ.get("TEACHBUDDY_CODEX"):
        return os.environ["TEACHBUDDY_CODEX"]
    im_pfad = shutil.which("codex")
    if im_pfad:
        return im_pfad
    treffer = sorted(glob.glob(CODEX_GLOB))
    if not treffer:
        raise AgentFehler(
            "Keine Codex-CLI gefunden (TEACHBUDDY_CODEX, PATH, %s) — der "
            "Skript-Agent läuft nach AUF-16 auf GPT." % CODEX_GLOB)
    return treffer[-1]


def rufe_agenten(*, material: str, thema: str, arbeit: str,
                 zeitgrenze_sek: int = 1800,
                 codex: str | None = None) -> tuple[str, str]:
    """Ruft den Skript-Agenten über `codex exec` (AUF-4, AUF-16).

    Der Auftrag (`auftrag.md`) und das Material werden nach `arbeit/`
    gelegt, der Agent läuft mit `--sandbox workspace-write` genau dort und
    schreibt `skript.md`. Der Prompt selbst bleibt kurz — der Auftrag steht
    in der versionierten Datei, nicht in einer Zeichenkette im Code (AUF-5).

    Liefert (skript_roh, modellkennung).
    """
    codex = codex or finde_codex()
    os.makedirs(arbeit, exist_ok=True)
    shutil.copyfile(AUFTRAG_PFAD, os.path.join(arbeit, "auftrag.md"))
    with open(os.path.join(arbeit, "material.md"), "w", encoding="utf-8") as f:
        f.write(material)
    ziel = os.path.join(arbeit, "skript.md")
    if os.path.exists(ziel):
        os.remove(ziel)

    prompt = (
        "Lies `auftrag.md` und `material.md` in diesem Verzeichnis und "
        "führe den Auftrag aus. Thema der Folge: %s. "
        "Schreibe das Ergebnis nach `skript.md` in diesem Verzeichnis. "
        "Lege nichts anderes an." % thema)

    # APP-11: Codex meldet seine Sandbox als `[workdir, /tmp, $TMPDIR]` und
    # legt Zwischendateien dort ab — also zeigt $TMPDIR ins Arbeitsverzeichnis.
    umgebung = dict(os.environ, TMPDIR=os.path.join(arbeit, "tmp"))
    os.makedirs(umgebung["TMPDIR"], exist_ok=True)

    try:
        lauf = subprocess.run(
            [codex, "exec", "--sandbox", "workspace-write",
             "--skip-git-repo-check", prompt],
            cwd=arbeit, capture_output=True, text=True, env=umgebung,
            timeout=zeitgrenze_sek)
    except FileNotFoundError as exc:
        raise AgentFehler("Codex-CLI nicht ausführbar: %s" % exc) from exc
    except subprocess.TimeoutExpired as exc:
        raise AgentFehler(
            "Skript-Agent hat nach %d s nicht geantwortet" % zeitgrenze_sek
        ) from exc

    with open(os.path.join(arbeit, "agent-ausgabe.log"), "w",
              encoding="utf-8") as f:
        f.write(lauf.stdout)
        if lauf.stderr:
            f.write("\n--- stderr ---\n" + lauf.stderr)

    if not os.path.exists(ziel):
        # AUF-20: Es wird nicht auf den anderen Kopf ausgewichen, und es
        # wird auch nicht aus der Konsolenausgabe zusammengeklaubt. Der
        # Auftrag scheitert mit Klartext.
        raise AgentFehler(
            "Skript-Agent hat keine `skript.md` geschrieben (Rückgabewert %d). "
            "Konsolenausgabe in %s"
            % (lauf.returncode, os.path.join(arbeit, "agent-ausgabe.log")))

    with open(ziel, encoding="utf-8") as f:
        roh = f.read()
    if not roh.strip():
        raise AgentFehler("Skript-Agent hat eine leere `skript.md` geschrieben")
    return roh, _modellkennung(codex, lauf.stdout + "\n" + (lauf.stderr or ""))


def _modellkennung(codex: str, ausgabe: str) -> str:
    """Welcher Kopf in welcher Fassung (AUF-18).

    Codex schreibt seinen Kopf (`OpenAI Codex v…`, `model: gpt-…`) nach
    **stderr**, nicht nach stdout — hier wird beides durchsucht. Ohne diese
    Zeile ist nach einem Modellwechsel nicht mehr erklärbar, warum der
    Podcast aus dem Frühjahr anders klingt als der von heute.
    """
    modell = re.search(r"^\s*model:\s*(\S+)", ausgabe, re.MULTILINE)
    cli = re.search(r"OpenAI Codex v(\S+)", ausgabe)
    if not cli:
        pfad = re.search(r"openai\.chatgpt-([\d.]+)", codex)
        cli = pfad
    return "codex %s / %s" % (cli.group(1) if cli else "?",
                              modell.group(1) if modell else "unbekannt")
