"""Sprachprobe — zählt, was „klingt vorgelesen" ausmacht (POD-17, E-25).

**Warum es das gibt.** Die Sprache wurde beim Testhören zweimal als sperrig
zurückgemeldet, und beide Male war die Antwort ein besser formulierter
Auftrag. Ob sich etwas bewegt hat, wusste danach niemand. Diese Probe macht
aus „klingt besser" fünf Zahlen, die man zwischen zwei Ständen vergleichen
kann.

**Sie blockiert nichts.** Eine Zahl sagt nicht, ob eine Folge hörenswert ist
— und jede
mechanische Probe lässt sich durch Konstruktion erfüllen. Wer den Nominalstil
mit Infinitiven umgeht, hat eine gute Zahl und keinen besseren Text.

Blockierend ist nur eines, und das steht woanders: `belegprobe.pruefe_vierte_wand`
(POD-18). Der Unterschied ist Absicht. Dass eine Folge über ihr eigenes
Material redet, ist ein **Fehler** und eindeutig erkennbar. Dass sie steif
klingt, ist ein **Urteil**.

Aufruf:

    python3 -m podcast.sprachprobe podcast/arbeit/*/skript.md
    python3 -m podcast.sprachprobe --alt podcast/arbeit        # Ausgangsstand
"""

from __future__ import annotations

import argparse
import dataclasses
import glob
import os
import re
import statistics
import sys

from . import belegprobe as belegprobe_mod
from . import skript as skript_mod

# POD-17b — Nominalstil. Vorgangsnomen, die im Sprechen ein Verb sein wollen.
NOMINAL_RE = re.compile(r"\b\w{4,}(ung|ungen|heit|heiten|keit|keiten)\b",
                        re.IGNORECASE)

# POD-17b — niemand handelt. Gemessen als Verhältnis, nicht absolut: Passiv
# ist nicht verboten, es soll nur nicht die Regel sein.
PASSIV_RE = re.compile(r"\b(wird|werden|wurde|wurden|worden)\b", re.IGNORECASE)
PERSON_RE = re.compile(r"\b(ich|du|wir|mir|mich|uns|dir|dich)\b", re.IGNORECASE)

# POD-17a — die Stelle, an der ein Begriff ein zweites Mal gesagt wird.
UMFORMULIERUNG_RE = re.compile(
    r"\b(also|das heißt|anders gesagt|anders formuliert|im Grunde"
    r"|einfach gesagt|vereinfacht|salopp|wenn man so will|sprich"
    r"|stell dir vor|man kann sich das vorstellen|bildlich|übersetzt)\b",
    re.IGNORECASE)

# POD-17c — der Bestätigungsreflex am Zeilenanfang.
FLOSKEL_RE = re.compile(r"^(genau|ja|richtig|absolut|stimmt|korrekt)\b[,.!… ]",
                        re.IGNORECASE)

# Ein Fragesatz, den die Sprachausgabe als Frage liest (POD-17d).
FRAGEWORT_RE = re.compile(
    r"^(was|wie|warum|wieso|weshalb|wer|wen|wem|wo|wohin|woran|worauf|wodurch"
    r"|womit|wann|welche[srnm]?|ist|sind|heißt|gibt|kann|muss|darf|hat|habe"
    r"|liegt|bleibt|und|aber|also|heißt)\b",
    re.IGNORECASE)


@dataclasses.dataclass(frozen=True)
class Befund:
    name: str
    nominal_je_100: float
    passiv_je_person: float
    umformulierungen: int
    nachgesagt: int
    floskel_anteil: float
    frage_mit_zeichen: float
    woerter: int
    saetze_median: float
    werkstatt: int

    @property
    def zeilen(self) -> list[str]:
        w = "—" if self.werkstatt == 0 else "%d ⚠" % self.werkstatt
        return [
            "  Nominalisierungen je 100 Wörter   %5.1f" % self.nominal_je_100,
            "  Passiv je persönliches Pronomen   %5.1f" % self.passiv_je_person,
            "  Umformulierungen in der Folge     %5d" % self.umformulierungen,
            "  Moderator sagt nach (POD-17a)     %5d" % self.nachgesagt,
            "  Gast-Zeilen mit Floskel-Auftakt   %4.0f %%" % (self.floskel_anteil * 100),
            "  Moderator-Fragen mit „?\"          %4.0f %%" % (self.frage_mit_zeichen * 100),
            "  Wörter gesprochen                 %5d" % self.woerter,
            "  Satzlänge (Median, Wörter)        %5.0f" % self.saetze_median,
            "  POD-18 Werkstatt-Befunde          %5s" % w,
        ]


def _saetze(text: str) -> list[str]:
    return [t.strip() for t in re.split(r"(?<=[.!?])\s+", text) if t.strip()]


def messe(skript: skript_mod.Skript, name: str) -> Befund:
    gast = [z for z in skript.zeilen if z.sprecher == "GAST"]
    mod = [z for z in skript.zeilen if z.sprecher == "MODERATOR"]
    alle_text = " ".join(z.sprechtext for z in skript.zeilen)
    gast_text = " ".join(z.sprechtext for z in gast)
    woerter = len(alle_text.split())

    # Nur Sätze des Moderators, die überhaupt eine Frage sein wollen: Ein
    # überleitender Aussagesatz braucht kein Fragezeichen, und ihn
    # mitzuzählen würde die Zahl bedeutungslos machen.
    fragend = [s for z in mod for s in _saetze(z.sprechtext)
               if FRAGEWORT_RE.match(s)]
    mit_zeichen = [s for s in fragend if "?" in s]

    # POD-17a in der Form, die Variante A vorsieht: Der Moderator sagt den
    # eben eingeführten Begriff mit eigenen Worten nach und fragt zurück.
    # Über Signalwörter ist dieser Zug nicht zu finden — er steckt in der
    # **Stellung**: eine Rückfrage des Moderators direkt auf eine Erklärung
    # des Gastes, ohne eigenen Beleg, weil sie nichts Neues behauptet.
    nachgesagt = 0
    zeilen = list(skript.zeilen)
    for vorige, diese in zip(zeilen, zeilen[1:]):
        if (vorige.sprecher == "GAST" and diese.sprecher == "MODERATOR"
                and "?" in diese.sprechtext
                and not diese.belege):
            nachgesagt += 1

    person = len(PERSON_RE.findall(gast_text)) or 1
    return Befund(
        name=name,
        nominal_je_100=len(NOMINAL_RE.findall(alle_text)) / max(woerter, 1) * 100,
        passiv_je_person=len(PASSIV_RE.findall(gast_text)) / person,
        umformulierungen=len(UMFORMULIERUNG_RE.findall(alle_text)),
        nachgesagt=nachgesagt,
        floskel_anteil=(sum(1 for z in gast if FLOSKEL_RE.match(z.sprechtext))
                        / max(len(gast), 1)),
        frage_mit_zeichen=len(mit_zeichen) / max(len(fragend), 1),
        woerter=woerter,
        saetze_median=statistics.median(
            [len(s.split()) for s in _saetze(alle_text)] or [0]),
        werkstatt=len(belegprobe_mod.pruefe_vierte_wand(skript)),
    )


def mittelwert(befunde: list[Befund], name: str) -> Befund:
    def m(feld: str) -> float:
        return statistics.mean(getattr(b, feld) for b in befunde)
    return Befund(
        name="%s (%d Folgen)" % (name, len(befunde)),
        nominal_je_100=m("nominal_je_100"),
        passiv_je_person=m("passiv_je_person"),
        umformulierungen=m("umformulierungen"),
        nachgesagt=int(m("nachgesagt")),
        floskel_anteil=m("floskel_anteil"),
        frage_mit_zeichen=m("frage_mit_zeichen"),
        woerter=int(m("woerter")),
        saetze_median=m("saetze_median"),
        werkstatt=sum(b.werkstatt for b in befunde),
    )


def lies_datei(pfad: str) -> Befund | None:
    try:
        s = skript_mod.lies(open(pfad, encoding="utf-8").read())
    except Exception:
        return None            # Ablehnung oder unfertig — nicht messbar
    return messe(s, os.path.basename(os.path.dirname(pfad)) or pfad)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("pfade", nargs="+", help="skript.md-Dateien oder ein Ordner")
    p.add_argument("--einzeln", action="store_true",
                   help="jede Folge zeigen, nicht nur den Mittelwert")
    a = p.parse_args(argv)

    dateien: list[str] = []
    for pf in a.pfade:
        if os.path.isdir(pf):
            dateien += sorted(glob.glob(os.path.join(pf, "*", "skript.md")))
        else:
            dateien.append(pf)

    befunde = [b for b in (lies_datei(d) for d in dateien) if b]
    if not befunde:
        print("Kein lesbares Skript gefunden.", file=sys.stderr)
        return 1

    if a.einzeln or len(befunde) == 1:
        for b in befunde:
            print(b.name)
            print("\n".join(b.zeilen))
            print()
    if len(befunde) > 1:
        g = mittelwert(befunde, "Mittel über alle")
        print(g.name)
        print("\n".join(g.zeilen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
