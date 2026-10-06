"""Belegprobe — auflösen oder scheitern (AUF-8, AUF-8b).

Das ist die technische Umsetzung von TB-1. Ohne sie ist die ganze
Bibliothek Dekoration: Das Modell würde am Ende doch aus dem eigenen
Gedächtnis erzählen, und niemand würde es merken.

Die Probe ist **mechanisch** (E-3), kein zweiter Agentenaufruf. Sie prüft
vier Dinge, und der erste ist der wichtigste:

  1. Eine Sprecherzeile ohne jeden Marker. Genau so sähe eine frei
     erfundene Passage aus.
  2. Ein `[B-…]`, das keine übergebene Einheit trägt — erfunden oder aus
     einer Einheit, die gar nicht übergeben wurde.
  3. Etwas in eckigen Klammern, das kein gültiger Marker ist. `[B-17]`
     ist kein Schreibfehler, sondern eine Beleghülse ohne Beleg.
  4. Am Sprechtext: dass nach dem Entfernen der Marker (AUF-8c) kein
     Belegapparat übrig ist. Das ist die Zusage aus POD-5 — im Audio wird
     nicht belegt —, und sie wird geprüft, nicht geglaubt.
  5. Am Sprechtext: dass die beiden nicht über ihre eigene Herstellung
     reden (POD-18). Siehe `pruefe_vierte_wand`.

Was die Probe **nicht** kann: beurteilen, ob eine Zeile das aussagt, was
ihr Beleg hergibt. Dafür ist nach AUF-16 das Gegenlesen durch den anderen
Kopf da. Die Probe schließt die Lücke, durch die Erfundenes unbemerkt
durchkommt, nicht die, durch die Falschverstandenes durchkommt.
"""

import dataclasses
import re

from . import einheiten as einheiten_mod
from . import skript as skript_mod

# POD-5: Was im gesprochenen Text nichts zu suchen hat. Der Marker selbst
# ist zu dem Zeitpunkt schon entfernt; hier geht es um das, was ein Agent
# stattdessen hineinschreibt, wenn er belegen will.
# POD-18: Die Folge spricht nie über ihre eigene Herstellung. Am 13.09.2026
# lief eine fertige Folge, in der der Moderator sagte, er habe
# keine Beispiele in den Daten; in 18 von 47 Folgen stand ein ganzer
# gesprochener Abschnitt über die Arbeitsanweisung.
#
# **Warum das eine blockierende Probe ist und keine Bitte an das Modell.**
# Die Anweisung im Auftrag lautete „sag das im Abschnitt ‚Wenn das Material
# nicht trägt'" — und Abschnitte werden vertont. Der Agent hat getan, was
# dastand. Eine Anweisung, die schon einmal so gelesen wurde, kann wieder so
# gelesen werden; deshalb steht hier eine Probe und nicht nur ein besserer
# Satz. Der Wortlaut ist eindeutig genug, um mechanisch zu greifen.
#
# Die Wörter sind mit Absicht eng gefasst: Es geht um die **Herstellung**.
# „Das Material, aus dem die Chips sind" wäre ein legitimer Satz über die
# Sache, deshalb steht `Material` nur in Verbindung mit einem Artikel oder
# Possessivum, wie es in den Leaks tatsächlich auftrat.
WERKSTATT_RE = re.compile(
    r"\b(das|dieses|unser|unserem|unseres|dem|des|im)\s+Material\b"
    r"|\bMaterial(basis|grenze|lage)\b"
    # Alle dreizehn Leaks lauteten woertlich „Der Auftrag verlangt". Eng
    # gefasst, weil „Auftragsverarbeitung" und „im Auftrag des Nutzers"
    # im Kapitel zur DSGVO voellig legitime Fachbegriffe sind.
    r"|\b(der|unser|dieser)\s+Auftrag\s+"
    r"(verlangt|will|sagt|fordert|schreibt|verbietet|erlaubt)\b"
    r"|\bWissenseinheit(en)?\b"
    r"|\bübergebene[nrs]?\s+(Einheiten|Material|Basis|Wissenseinheiten)\b"
    r"|\bQuellenlage\b"
    r"|\bBeleg(e|en|marker|apparat)?\s+"
    r"(fehlt|fehlen|liegt|liegen|trägt|tragen|steht|stehen)\b"
    r"|\b(nicht|nichts)\s+belegt\b|\bnicht\s+belegbar\b",
    re.IGNORECASE)

QUELLENAPPARAT_RE = re.compile(
    r"B-\d{4}-\d{2}"
    r"|\bvgl\.\s"
    r"|\bebd\.\b"
    r"|\bS\.\s?\d+"
    r"|\bet\s+al\.",
    re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class Befund:
    art: str
    ort: str
    text: str

    def __str__(self) -> str:
        return "[%s] %s: %s" % (self.art, self.ort, self.text)


@dataclasses.dataclass(frozen=True)
class Probe:
    bestanden: bool
    befunde: tuple[Befund, ...]
    belege_verwendet: tuple[str, ...]
    einheiten_verwendet: tuple[str, ...]
    einheiten_ungenutzt: tuple[str, ...]

    def bericht(self) -> str:
        kopf = ("Belegprobe bestanden" if self.bestanden
                else "Belegprobe GESCHEITERT (%d Befunde)" % len(self.befunde))
        zeilen = [
            "# " + kopf,
            "",
            "- Belege verwendet: %d (%s)"
            % (len(self.belege_verwendet), ", ".join(self.belege_verwendet)),
            "- Einheiten verwendet: %d (%s)"
            % (len(self.einheiten_verwendet),
               ", ".join(self.einheiten_verwendet) or "—"),
            "- Einheiten ungenutzt: %s"
            % (", ".join(self.einheiten_ungenutzt) or "keine"),
        ]
        if self.befunde:
            zeilen += ["", "## Befunde", ""]
            zeilen += ["- " + str(b) for b in self.befunde]
        return "\n".join(zeilen) + "\n"


def pruefe(skript: skript_mod.Skript,
           einheiten: list[einheiten_mod.Wissenseinheit]) -> Probe:
    """Hält jede Sprecherzeile gegen die übergebenen Wissenseinheiten."""
    register = einheiten_mod.belegregister(einheiten)
    befunde: list[Befund] = []
    belege_verwendet: set[str] = set()
    einheiten_verwendet: set[str] = set()

    for abschnitt in skript.abschnitte:
        for zeile in abschnitt.zeilen:
            ort = "Zeile %d (%s)" % (zeile.zeilennummer, zeile.sprecher)

            if not zeile.marker:
                befunde.append(Befund(
                    "ohne-marker", ort,
                    "Sprecherzeile ohne jeden Marker — so sähe eine "
                    "erfundene Passage aus: %r" % _kurz(zeile.text)))

            for klammer in skript_mod.KLAMMER_RE.findall(zeile.text):
                if not skript_mod.MARKER_RE.fullmatch(klammer):
                    befunde.append(Befund(
                        "kein-marker", ort,
                        "%r ist kein gültiger Marker (erwartet [B-nnnn-nn] "
                        "oder [E])" % klammer))

            for beleg in zeile.belege:
                if beleg not in register:
                    befunde.append(Befund(
                        "unaufloesbar", ort,
                        "%s trägt keine der übergebenen Einheiten" % beleg))
                    continue
                belege_verwendet.add(beleg)
                einheiten_verwendet.update(register[beleg])

    befunde += pruefe_sprechtext(skript)
    befunde += pruefe_vierte_wand(skript)

    alle = {e.id for e in einheiten}
    return Probe(
        bestanden=not befunde,
        befunde=tuple(befunde),
        belege_verwendet=tuple(sorted(belege_verwendet)),
        einheiten_verwendet=tuple(sorted(einheiten_verwendet)),
        einheiten_ungenutzt=tuple(sorted(alle - einheiten_verwendet)),
    )


def pruefe_sprechtext(skript: skript_mod.Skript) -> list[Befund]:
    """POD-5 — im Audio wird nicht belegt.

    Läuft auf dem Text, der nach AUF-8c in die Sprachausgabe geht. Fängt
    zweierlei: einen Marker, den `ohne_marker` nicht erwischt hat, und
    einen Agenten, der die Quelle in Prosa hineingeschrieben hat.
    """
    befunde = []
    for zeile in skript.zeilen:
        treffer = QUELLENAPPARAT_RE.search(zeile.sprechtext)
        if treffer:
            befunde.append(Befund(
                "beleg-im-audio",
                "Zeile %d (%s)" % (zeile.zeilennummer, zeile.sprecher),
                "Quellenangabe %r bliebe im gesprochenen Text stehen "
                "(POD-5)" % treffer.group(0)))
    return befunde


def pruefe_vierte_wand(skript: skript_mod.Skript) -> list[Befund]:
    """POD-18 — die Folge spricht nie über ihre eigene Herstellung.

    Zwei Dinge werden gefangen, und das zweite ist das gröbere:

    * eine Sprecherzeile, die vom Material, vom Auftrag oder von Belegen
      redet,
    * eine **Abschnittsüberschrift** darüber. Die wird dem Hörer als
      Kapitelmarke angezeigt (Regel 5 des Auftrags), also ist sie der
      sichtbarste Ort, an dem das schiefgehen kann — und genau dort ist es
      achtzehnmal schiefgegangen.

    Der ehrliche Satz über die Sache bleibt erlaubt: „Dazu gibt es bisher
    kaum belastbare Zahlen" redet über den Forschungsstand. Gefangen wird
    „das steht nicht in unserem Material", weil der Satz über *uns* redet.
    """
    befunde = []
    for abschnitt in skript.abschnitte:
        treffer = WERKSTATT_RE.search(abschnitt.titel)
        if treffer:
            befunde.append(Befund(
                "werkstatt-als-kapitel",
                "Abschnitt %r" % abschnitt.titel,
                "Die Überschrift redet über die Herstellung (%r) und wird "
                "dem Hörer als Kapitelmarke angezeigt (POD-18)"
                % treffer.group(0)))
        for zeile in abschnitt.zeilen:
            treffer = WERKSTATT_RE.search(zeile.sprechtext)
            if treffer:
                befunde.append(Befund(
                    "werkstatt-im-audio",
                    "Zeile %d (%s)" % (zeile.zeilennummer, zeile.sprecher),
                    "%r redet über die eigene Herstellung — der Hörer kennt "
                    "diese Begriffe nicht (POD-18): %s"
                    % (treffer.group(0), _kurz(zeile.sprechtext))))
    return befunde


def _kurz(text: str, n: int = 70) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[:n - 1] + "…"
