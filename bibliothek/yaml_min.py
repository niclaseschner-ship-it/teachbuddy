"""Ein YAML-Leser fuer genau die Teilmenge, die im Frontmatter vorkommt.

Warum nicht PyYAML: Die Randbedingung des Auftrags ist "Flask, sonst
Standardbibliothek". Das Frontmatter der Bibliothek ist eng: Skalare,
Flow-Listen (``[a, b]``), **flache** Flow-Abbildungen (``{a: 1, b: 2}``, seit
``lektionen/L-*.md`` die Sprecherbesetzung so fuehrt), Block-Listen (``- a``)
und gefaltete Bloecke (``>`` / ``|``). Mehr kommt im echten Material nicht vor.

Der Leser ist absichtlich **streng**: Was er nicht kennt, wirft er als
``YamlFehler``. Ein Parser, der raet, verletzt Regel 2 aus CONTRIBUTING.md an der
Stelle, an der es am wenigsten auffaellt.
"""

from __future__ import annotations

import re

__all__ = ["YamlFehler", "lies_block", "trenne_frontmatter"]


class YamlFehler(ValueError):
    """Das Frontmatter enthaelt etwas, das dieser Leser nicht kennt."""


_SCHLUESSEL = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*):(?P<rest>.*)$")
_FRONTMATTER = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)


def trenne_frontmatter(text: str) -> tuple[str | None, str]:
    """Zerlegt einen Dateiinhalt in Frontmatter-Block und Rumpf.

    Ohne Frontmatter ist der erste Rueckgabewert ``None`` und der Rumpf der
    ganze Text.
    """
    treffer = _FRONTMATTER.match(text)
    if not treffer:
        return None, text
    return treffer.group(1), text[treffer.end():]


def lies_block(block: str, *, herkunft: str = "<unbekannt>") -> dict[str, object]:
    """Liest einen YAML-Block der bekannten Teilmenge in ein dict."""
    zeilen = block.replace("\r\n", "\n").split("\n")
    ergebnis: dict[str, object] = {}
    i = 0
    while i < len(zeilen):
        zeile = zeilen[i]
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            i += 1
            continue
        if zeile[:1] in (" ", "\t"):
            raise YamlFehler(
                f"{herkunft}: Zeile {i + 1} ist eingerueckt, aber es steht kein "
                f"Block-Schluessel davor: {zeile!r}"
            )
        treffer = _SCHLUESSEL.match(zeile)
        if not treffer:
            raise YamlFehler(f"{herkunft}: Zeile {i + 1} ist kein 'schluessel: wert': {zeile!r}")

        schluessel = treffer.group("key")
        rest = treffer.group("rest").strip()

        if rest in (">", "|", ">-", "|-", ">+", "|+"):
            wert, i = _lies_block_skalar(zeilen, i + 1, rest[0], herkunft)
        elif rest == "":
            wert, i = _lies_eingerueckten_wert(zeilen, i + 1, herkunft)
        else:
            wert = _lies_flow(rest, herkunft, i + 1)
            i += 1

        if schluessel in ergebnis:
            raise YamlFehler(f"{herkunft}: Schluessel {schluessel!r} kommt doppelt vor")
        ergebnis[schluessel] = wert
    return ergebnis


def _einzug(zeile: str) -> int:
    return len(zeile) - len(zeile.lstrip(" "))


def _lies_block_skalar(zeilen: list[str], i: int, art: str, herkunft: str) -> tuple[str, int]:
    """Sammelt einen ``>``- oder ``|``-Block ein."""
    gesammelt: list[str] = []
    einzug: int | None = None
    while i < len(zeilen):
        zeile = zeilen[i]
        if not zeile.strip():
            gesammelt.append("")
            i += 1
            continue
        if einzug is None:
            einzug = _einzug(zeile)
            if einzug == 0:
                break
        if _einzug(zeile) < einzug:
            break
        gesammelt.append(zeile[einzug:])
        i += 1

    while gesammelt and not gesammelt[-1]:
        gesammelt.pop()
    if art == "|":
        return "\n".join(gesammelt), i
    # gefaltet: Leerzeilen trennen Absaetze, sonst wird zusammengezogen
    absaetze: list[list[str]] = [[]]
    for zeile in gesammelt:
        if zeile:
            absaetze[-1].append(zeile)
        elif absaetze[-1]:
            absaetze.append([])
    return "\n\n".join(" ".join(a) for a in absaetze if a), i


def _lies_eingerueckten_wert(zeilen: list[str], i: int, herkunft: str,
                             mindest_einzug: int = 1) -> tuple[object, int]:
    """Nach ``schluessel:`` ohne Wert folgt eine Block-Liste oder nichts.

    Ein Eintrag ist entweder ein Skalar (``- WE-0001``) oder eine flache
    Abbildung ueber mehrere Zeilen::

        achsen:
          - id: A1
            frage: Wer urteilt?
            einheiten: [WE-0001, WE-0004]

    Tiefer als eine Ebene geht es nicht. Die Mindmap-Analyse (E-19a) braucht
    genau diese Form; alles darueber hinaus waere Vorrat (TB-9).
    """
    eintraege: list[object] = []
    while i < len(zeilen):
        zeile = zeilen[i]
        if not zeile.strip():
            i += 1
            continue
        # Faellt die Einrueckung unter die des Elternteils, ist die Liste zu
        # Ende. Ohne diese Grenze zieht eine verschachtelte Liste die
        # naechsten Geschwister des Elternteils in sich hinein.
        if _einzug(zeile) < mindest_einzug:
            break
        gestutzt = zeile.strip()
        if not gestutzt.startswith("- "):
            raise YamlFehler(
                f"{herkunft}: Zeile {i + 1} ist eingerueckt, aber kein Listeneintrag "
                f"('- …'): {zeile!r}"
            )
        kopf = gestutzt[2:].strip()
        # Ein Listeneintrag mit `schluessel: wert` eroeffnet eine Abbildung.
        # Ihre Folgezeilen stehen tiefer eingerueckt als der Strich selbst.
        paar = _paar(kopf)
        if paar is None:
            eintraege.append(_skalar(kopf))
            i += 1
            continue
        strich_einzug = _einzug(zeile)
        abbildung: dict[str, object] = {paar[0]: _lies_flow(paar[1], herkunft, i + 1)}
        i += 1
        while i < len(zeilen):
            folge = zeilen[i]
            if not folge.strip():
                i += 1
                continue
            if _einzug(folge) <= strich_einzug:
                break
            weiter = _paar(folge.strip())
            if weiter is None:
                raise YamlFehler(
                    f"{herkunft}: Zeile {i + 1} gehoert zu einem Listeneintrag, "
                    f"ist aber kein 'schluessel: wert': {folge!r}"
                )
            if weiter[1] == "":
                # Ein Schluessel ohne Wert eroeffnet eine eingerueckte Liste.
                # Die Mindmap-Analyse braucht das seit dem 12.09.2026: Bei 178
                # Einheiten traegt eine flache Achsenliste nicht mehr, es
                # braucht Unterachsen.
                unter, i = _lies_eingerueckten_wert(
                    zeilen, i + 1, herkunft, mindest_einzug=_einzug(folge) + 1)
                abbildung[weiter[0]] = unter
                continue
            abbildung[weiter[0]] = _lies_flow(weiter[1], herkunft, i + 1)
            i += 1
        eintraege.append(abbildung)
    return eintraege, i


def _paar(text: str) -> tuple[str, str] | None:
    """``schluessel: wert`` zerlegen, sonst None.

    Der Doppelpunkt muss von einem Leerzeichen gefolgt sein. Sonst waere
    ``https://example.org`` ein Schluessel.
    """
    stelle = text.find(": ")
    if stelle <= 0:
        if text.endswith(":") and len(text) > 1 and " " not in text[:-1]:
            return text[:-1], ""
        return None
    schluessel = text[:stelle].strip()
    if not schluessel or " " in schluessel:
        return None
    return schluessel, text[stelle + 2:].strip()


def _lies_flow(rest: str, herkunft: str, zeilennr: int) -> object:
    if rest.startswith("["):
        if not rest.endswith("]"):
            raise YamlFehler(
                f"{herkunft}: Zeile {zeilennr}: Flow-Liste ueber mehrere Zeilen kennt "
                f"dieser Leser nicht: {rest!r}"
            )
        inhalt = rest[1:-1].strip()
        if not inhalt:
            return []
        return [_skalar(t.strip()) for t in inhalt.split(",")]
    if rest.startswith("{"):
        return _lies_flow_abbildung(rest, herkunft, zeilennr)
    return _skalar(rest)


def _lies_flow_abbildung(rest: str, herkunft: str, zeilennr: int) -> dict[str, str]:
    """``{MODERATOR: shimmer, GAST: onyx}`` — flach, ein Doppelpunkt je Paar.

    Verschachtelung bleibt ungelesen: Sie kommt im Material nicht vor, und ein
    Leser, der sie halb koennte, wuerde bei der ersten echten Verschachtelung
    etwas Plausibles liefern statt zu widersprechen.
    """
    if not rest.endswith("}"):
        raise YamlFehler(
            f"{herkunft}: Zeile {zeilennr}: Flow-Abbildung ueber mehrere Zeilen kennt "
            f"dieser Leser nicht: {rest!r}"
        )
    inhalt = rest[1:-1].strip()
    if not inhalt:
        return {}
    if "{" in inhalt or "[" in inhalt:
        raise YamlFehler(
            f"{herkunft}: Zeile {zeilennr}: verschachtelte Flow-Abbildungen kennt "
            f"dieser Leser nicht: {rest!r}"
        )
    paare: dict[str, str] = {}
    for teil in inhalt.split(","):
        if ":" not in teil:
            raise YamlFehler(
                f"{herkunft}: Zeile {zeilennr}: {teil.strip()!r} ist kein 'a: b' in "
                f"der Flow-Abbildung {rest!r}"
            )
        name, wert = teil.split(":", 1)
        name = _skalar(name.strip())
        if name in paare:
            raise YamlFehler(
                f"{herkunft}: Zeile {zeilennr}: Schluessel {name!r} kommt in der "
                f"Flow-Abbildung doppelt vor"
            )
        paare[name] = _skalar(wert.strip())
    return paare


def _skalar(roh: str) -> str:
    """Alle Skalare bleiben Text.

    Datumsangaben werden **nicht** in ``date`` gewandelt: Im Material steht
    neben ``2023-06-09`` auch ``unbekannt`` (BIB-2), und ein Feld, das mal
    Datum und mal Text ist, macht jede Abfrage darauf zur Fallunterscheidung.
    ISO-Text sortiert ohnehin richtig.
    """
    if len(roh) >= 2 and roh[0] == roh[-1] and roh[0] in ("'", '"'):
        return roh[1:-1]
    return roh
