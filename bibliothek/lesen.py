"""Liest die Bibliothek aus Dateien (BIB-18, E-9).

Dieser Leser richtet sich nach dem **echten Material** in
der Bibliothek (``TEACHBUDDY_WISSEN``), nicht nach der Idealform aus ``specs/bibliothek.md``.
Wo beides auseinandergeht, entsteht ein :class:`Befund` — kein stiller
Notbehelf. Die Befunde landen im Index (Tabelle ``befunde``).

Was gelesen wird (BIB-25, BIB-26):

    Quelle · Quellenversion · Fundstelle · Beleg · Wissenseinheit · Lernpfad
    · Lektion

Begriffe und Lernziele als eigene Knoten sind bewusst nicht dabei. Die
**Lektion** ist seit ``eingang/M-001/lektionen/L-F01.md`` da: Sie nennt ihre
Wissenseinheiten in Reihenfolge (BIB-27), und nur sie — eine Wissenseinheit
weisz nicht, in welchen Lektionen sie vorkommt. Diese Rueckwaertsfrage
beantwortet der Index (``bibliothek/abfragen.py``), nicht die Datei.

Das Kapitel hat weiterhin keine eigene Dateiform: Es ist der Abschnitt eines
Lernpfads, bezeichnet durch einen Buchstaben, nicht durch eine ``K-``-ID.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .yaml_min import YamlFehler, lies_block, trenne_frontmatter

__all__ = [
    "Befund",
    "Beleg",
    "Bibliothek",
    "Fundstelle",
    "Kapitelmarke",
    "Lektion",
    "Lernpfad",
    "Abschnitt",
    "Quelle",
    "Quellenversion",
    "Wissenseinheit",
    "lies_bibliothek",
]

FREIGEGEBEN = "freigegeben"

# R-10: Eine Kapitelmarke traegt ihre Bedeutung in 'art', nicht im Titeltext.
MARKEN_ARTEN = frozenset({"einleitung", "inhalt", "zusammenfassung"})

# Kantentypen aus BIB-22. Alles ausserhalb dieser Liste wird als Befund gemeldet.
BIB22_TYPEN = frozenset(
    {
        "stuetzt",
        "widerspricht",
        "praezisiert",
        "ersetzt",
        "handelt_von",
        "setzt_voraus",
        "dient_lernziel",
        "prueft",
    }
)


# BIB-11: Absatzgrenze im Inhalt und ein Beleg irgendwo darin.
_ABSATZ_INHALT = re.compile(r"\n\s*\n")
_BELEG_IM_TEXT = re.compile(r"\[B-\d{4}-\d{2}\]")


@dataclass(frozen=True)
class Befund:
    """Eine Abweichung zwischen Material und Spec, oder ein Lesefehler."""

    art: str
    schwere: str  # "hinweis" | "abweichung" | "fehler"
    betrifft: str
    text: str


@dataclass
class Quelle:
    id: str
    titel: str
    urheber: str
    art: str
    fundort: str
    veroeffentlicht: str
    abgerufen: str
    lizenz: str
    qualitaet: str
    qualitaet_begruendung: str
    reichweite: str | None
    reichweite_detail: str | None
    anmerkung: str
    herkunft: str
    pfad: str


@dataclass
class Quellenversion:
    """Eine gesicherte Fassung einer Quelle (BIB-4a).

    ``id`` ist der Dateiname (``V-2026-09-10``) und damit **nur innerhalb
    einer Quelle** eindeutig — im Material tragen 28 Versionsdateien
    zusammen zwei verschiedene Namen. ``schluessel`` ist der global
    eindeutige Schluessel ``<quelle>/<id>``.
    """

    id: str
    schluessel: str
    quelle_id: str
    zeichen: int
    herkunft: str
    pfad: str


@dataclass
class Fundstelle:
    id: str
    quelle_id: str
    version_id: str
    stelle: str
    zitat: str
    anmerkung: str
    herkunft: str
    pfad: str


@dataclass
class Beleg:
    id: str
    fundstelle_id: str
    gilt_ab: str
    zuversicht: str
    aussage: str
    begruendung: str
    herkunft: str
    pfad: str


@dataclass
class Wissenseinheit:
    id: str
    titel: str
    grad: str
    # MMP-3: Das Stichwort ist die Beschriftung in der Mindmap. Der ``titel``
    # taugt dafuer nicht — er ist nach dem Mikropublikations-Modell eine
    # Behauptung, also ein ganzer Satz. Es entsteht in der Strukturanalyse
    # (auftraege/mindmap-analyse.md), nicht beim Rendern.
    stichwort: str
    belegt_durch: list[str]
    setzt_voraus: list[str]
    widerspricht: list[str]
    siehe_auch: list[str]
    gilt_ab: str
    kurzfassung: str
    inhalt: str
    prueffrage: str
    herkunft: str
    pfad: str


@dataclass
class Abschnitt:
    """Ein Abschnitt eines Lernpfads — im Material A bis M, ohne ``K-``-ID."""

    schluessel: str
    nummer: int
    titel: str
    kern: str
    text: str


@dataclass
class Lernpfad:
    id: str
    titel: str
    kurzfassung: str
    status: str
    sprache: str
    abschnitte: list[Abschnitt]
    kopf: dict[str, object]
    pfad: str
    # In welcher Reihenfolge gelernt wird, nicht in welcher gebaut wurde.
    # P-01 entstand zuerst, gehoert aber hinter die Grundlagen aus P-02.
    reihenfolge: int = 99


@dataclass(frozen=True)
class Kapitelmarke:
    """Eine Sprungmarke im Audio einer Lektion (R-10).

    Die Bedeutung steht in ``art``, nicht im Titeltext — ein Titel wie
    „Verbosity Bias — strittig" liesze sich sonst nur durch Raten in Marke und
    Merkmal zerlegen.
    """

    sek: int
    titel: str
    art: str


@dataclass
class Lektion:
    """Eine Podcast-Folge samt ihren Wissenseinheiten (BIB-26, BIB-27).

    ``wissenseinheiten`` ist **geordnet**: Die Reihenfolge ist die, in der die
    Folge sie behandelt, und damit eine Aussage der Lektion — keine Menge.

    ``kapitel`` ist seit dem 12.09.2026 eine **Kapitel-ID** (``K-01``), nicht
    mehr ein Abschnittsbuchstabe: Ein Abschnitt ist eine Lektion, kein Kapitel
    (BIB-26). Welcher Abschnitt des Lernpfads diese Lektion ausfuellt, steht in
    ``abschnitt``.

    ``pfad_id`` steht nicht im Frontmatter. Es wird ueber das Kapitel
    erschlossen (siehe :func:`_ordne_lektionen_zu`).
    """

    id: str
    kapitel: str
    abschnitt: str
    nummer: int | None
    titel: str
    dauer_sek: int | None
    wissenseinheiten: list[str]
    audio: str
    auftrag: str
    zeichen_vertont: int | None
    stimmen: dict[str, str]
    erzeugt: str
    # AUF-18a: Fassung der Podcast-Pipeline, mit der diese Folge gebaut wurde.
    # Leer bei allem, was vor dem 13.09.2026 entstand — das ist ehrlicher als
    # eine Eins hineinzuschreiben, die niemand gemessen hat.
    pipeline: int | None
    kapitelmarken: list[Kapitelmarke]
    pfad_id: str
    herkunft: str
    pfad: str
    # OBF-9: die Uebersichtsgrafik. Eigenstaendiges HTML-Dokument, das offline
    # tragen muss — keine fremden Stylesheets, keine Schriften von aussen (R-7).
    bild: str | None = None
    bild_breite: int | None = None
    bild_hoehe: int | None = None
    bild_titel: str | None = None
    bild_belege: list[str] = field(default_factory=list)



@dataclass
class Kapitel:
    """Die Ebene, die BIB-26 vorsieht und die bis zum 12.09.2026 fehlte.

    Ein Kapitel hat **mehrere Lektionen, eine Mindmap und einen
    Diskussionspartner**. Die dreizehn Abschnitte eines Lernpfads sind
    Lektionen, keine Kapitel: Ein Abschnitt ist eine Podcast-Folge von 5 bis
    10 Minuten, und das ist die Groesse einer Lektion.
    """

    id: str
    pfad_id: str
    nummer: int
    titel: str
    kurzfassung: str
    lektionen: list[str]          # Abschnittsschluessel in Reihenfolge
    pfad: str


@dataclass
class Mindmapachse:
    """Eine Gliederungsachse der Mindmap — als Frage, nicht als Substantiv."""

    id: str
    frage: str
    einheiten: list[str]
    # Die uebergeordnete Achse, wenn die Analyse zwei Ebenen hat (MMP-10a).
    eltern: str | None = None
    eltern_frage: str | None = None


@dataclass
class Mindmapanalyse:
    """Die Strukturanalyse eines Kapitels (E-19a, auftraege/mindmap-analyse.md).

    Sie ist **Daten, kein Bild**: MMP-8 und E-19b halten fest, dass die
    Mindmap eine Ansicht auf den Begriffsgraphen bleibt. Was hier liegt, ist
    die Gliederung, nach der gezeichnet wird — nicht die Zeichnung.
    """

    kapitel: str
    kern: str
    achsen: list[Mindmapachse]
    kernaussage: str
    beziehungen: str
    layout: str
    pfad: str
    # Eine gebaute Grafik, falls vorhanden (E-24, Nachtrag). Eigenstaendiges
    # HTML-Dokument wie das Bild einer Lektion, nur groesser: Es ist die
    # Uebersicht ueber ein ganzes Kapitel.
    bild: str | None = None
    bild_breite: int | None = None
    bild_hoehe: int | None = None
    bild_titel: str | None = None
    bild_belege: list[str] = field(default_factory=list)


@dataclass
class Bibliothek:
    wurzel: str
    quellen: dict[str, Quelle] = field(default_factory=dict)
    versionen: dict[str, Quellenversion] = field(default_factory=dict)
    fundstellen: dict[str, Fundstelle] = field(default_factory=dict)
    belege: dict[str, Beleg] = field(default_factory=dict)
    einheiten: dict[str, Wissenseinheit] = field(default_factory=dict)
    lektionen: dict[str, Lektion] = field(default_factory=dict)
    pfade: dict[str, Lernpfad] = field(default_factory=dict)
    kapitel: dict[str, Kapitel] = field(default_factory=dict)
    mindmaps: dict[str, Mindmapanalyse] = field(default_factory=dict)
    befunde: list[Befund] = field(default_factory=list)

    def melde(self, art: str, schwere: str, betrifft: str, text: str) -> None:
        self.befunde.append(Befund(art, schwere, betrifft, text))


# --------------------------------------------------------------------------
# Einstieg
# --------------------------------------------------------------------------


def lies_bibliothek(wurzel: str | Path) -> Bibliothek:
    """Liest das ganze Repo der Bibliothek (``TEACHBUDDY_WISSEN``) ein."""
    wurzel = Path(wurzel).resolve()
    if not wurzel.is_dir():
        raise FileNotFoundError(f"Bibliothekswurzel fehlt: {wurzel}")
    bib = Bibliothek(wurzel=str(wurzel))

    # Reihenfolge ist Vorrangfolge: spaeter gelesen verdraengt frueher gelesen.
    # Eingangsauftraege lexikalisch (A-001 < A-002 < …), Freigegebenes zuletzt.
    bereiche: list[tuple[str, Path]] = []
    eingang = wurzel / "eingang"
    if eingang.is_dir():
        for d in sorted(p for p in eingang.iterdir() if p.is_dir()):
            bereiche.append((d.name, d))
    bereiche.append((FREIGEGEBEN, wurzel))

    for herkunft, basis in bereiche:
        _lies_quellen(bib, basis, herkunft)
        _lies_belege(bib, basis, herkunft)
        _lies_einheiten(bib, basis, herkunft)
        _lies_lektionen(bib, basis, herkunft)

    _lies_pfade(bib, wurzel)
    _lies_kapitel(bib, wurzel)
    _lies_mindmaps(bib, wurzel, "bibliothek")
    # Erst jetzt: Eine Lektion nennt ihr Kapitel, nicht ihren Lernpfad. Zu
    # welchem Lernpfad das Kapitel gehoert, steht in kapitel/ — eben gelesen.
    _ordne_lektionen_zu(bib)
    _pruefe_zusammenhang(bib)
    return bib


# --------------------------------------------------------------------------
# Quellen, Versionen, Fundstellen
# --------------------------------------------------------------------------


def _lies_quellen(bib: Bibliothek, basis: Path, herkunft: str) -> None:
    ordner = basis / "quellen"
    if not ordner.is_dir():
        return
    for q_dir in sorted(p for p in ordner.iterdir() if p.is_dir()):
        datei = q_dir / "quelle.md"
        if not datei.is_file():
            bib.melde(
                "quelle_ohne_kopf",
                "fehler",
                q_dir.name,
                f"{_rel(bib, q_dir)} hat keine quelle.md",
            )
            continue
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        qid = str(kopf.get("id") or q_dir.name)
        _verdraengt(bib, bib.quellen, qid, herkunft, "Quelle", datei)
        fehlend = [
            k
            for k in ("titel", "urheber", "art", "fundort", "veroeffentlicht", "abgerufen")
            if not kopf.get(k)
        ]
        if fehlend:
            bib.melde(
                "quelle_unvollstaendig",
                "abweichung",
                qid,
                "BIB-1 verlangt Titel, Urheber, Art, Fundort, Datum; es fehlen: "
                + ", ".join(fehlend),
            )
        if kopf.get("reichweite") is None:
            bib.melde(
                "reichweite_fehlt",
                "abweichung",
                qid,
                "BIB-4d verlangt eine Reichweite (volltext | teilweise | nur-abstract); "
                f"{_rel(bib, datei)} hat keine.",
            )
        bib.quellen[qid] = Quelle(
            id=qid,
            titel=_text(kopf.get("titel")),
            urheber=_text(kopf.get("urheber")),
            art=_text(kopf.get("art")),
            fundort=_text(kopf.get("fundort")),
            veroeffentlicht=_text(kopf.get("veroeffentlicht")),
            abgerufen=_text(kopf.get("abgerufen")),
            lizenz=_text(kopf.get("lizenz")),
            qualitaet=_text(kopf.get("qualitaet")),
            qualitaet_begruendung=_text(kopf.get("qualitaet_begruendung")),
            # BIB-2: nicht ermittelt ist etwas anderes als leer. Fehlt das
            # Feld, bleibt es None und der Befund 'reichweite_fehlt' steht.
            reichweite=_text(kopf.get("reichweite")) or None,
            reichweite_detail=_text(kopf.get("reichweite_detail")) or None,
            anmerkung=_rumpf(datei),
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )
        _lies_versionen(bib, q_dir, qid, herkunft)
        _lies_fundstellen(bib, q_dir / "fundstellen.md", qid, herkunft)


def _lies_versionen(bib: Bibliothek, q_dir: Path, qid: str, herkunft: str) -> None:
    ordner = q_dir / "versionen"
    if not ordner.is_dir():
        bib.melde(
            "version_fehlt",
            "abweichung",
            qid,
            f"BIB-4/4a: {_rel(bib, q_dir)} hat keinen Ordner versionen/",
        )
        return
    for datei in sorted(ordner.glob("*.md")):
        vid = datei.stem
        schluessel = f"{qid}/{vid}"
        roh = datei.read_text(encoding="utf-8", errors="replace")
        _verdraengt(bib, bib.versionen, schluessel, herkunft, "Quellenversion", datei)
        bib.versionen[schluessel] = Quellenversion(
            id=vid,
            schluessel=schluessel,
            quelle_id=qid,
            zeichen=len(roh),
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )


_FUNDSTELLE_KOPF = re.compile(r"^##\s+(F-\S+)\s*$")
_FELD = re.compile(r"^([A-Za-zÄÖÜäöü][A-Za-z0-9_]*):(.*)$")


def _lies_fundstellen(bib: Bibliothek, datei: Path, qid: str, herkunft: str) -> None:
    """``fundstellen.md`` ist **kein** Frontmatter-Dokument.

    Das echte Material legt je Quelle *eine* Datei mit ``## F-xxxx-yy``-
    Abschnitten an, darin ``stelle:``/``version:``/``zitat: >`` und
    gelegentlich ein freier ``Anmerkung:``-Absatz. Deshalb ein eigener Leser
    statt :func:`yaml_min.lies_block`.
    """
    if not datei.is_file():
        bib.melde(
            "fundstellen_fehlen",
            "abweichung",
            qid,
            f"BIB-7: zu {qid} gibt es keine fundstellen.md",
        )
        return

    zeilen = datei.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
    aktuell: str | None = None
    block: list[str] = []

    def abschliessen() -> None:
        if aktuell is None:
            return
        felder, anmerkung = _fundstellen_block(block)
        if "zitat" not in felder:
            bib.melde(
                "fundstelle_ohne_zitat",
                "fehler",
                aktuell,
                f"BIB-8 verlangt den Wortlaut; {_rel(bib, datei)} hat zu {aktuell} kein zitat.",
            )
        _verdraengt(bib, bib.fundstellen, aktuell, herkunft, "Fundstelle", datei)
        bib.fundstellen[aktuell] = Fundstelle(
            id=aktuell,
            quelle_id=qid,
            version_id=felder.get("version", ""),
            stelle=felder.get("stelle", ""),
            zitat=felder.get("zitat", ""),
            anmerkung=anmerkung,
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )

    for zeile in zeilen:
        kopf = _FUNDSTELLE_KOPF.match(zeile)
        if kopf:
            abschliessen()
            aktuell = kopf.group(1)
            block = []
        elif aktuell is not None:
            block.append(zeile)
    abschliessen()


def _fundstellen_block(zeilen: list[str]) -> tuple[dict[str, str], str]:
    felder: dict[str, str] = {}
    anmerkung: list[str] = []
    i = 0
    while i < len(zeilen):
        zeile = zeilen[i]
        treffer = _FELD.match(zeile)
        if not treffer:
            if zeile.strip() and anmerkung:
                anmerkung.append(zeile.strip())
            i += 1
            continue
        name = treffer.group(1).lower()
        rest = treffer.group(2).strip()
        if rest in (">", "|"):
            wert, i = _eingerueckter_block(zeilen, i + 1, gefaltet=rest == ">")
            felder[name] = wert
            continue
        if name == "anmerkung":
            anmerkung = [rest]
            i += 1
            continue
        felder[name] = rest
        i += 1
    return felder, " ".join(anmerkung).strip()


def _eingerueckter_block(zeilen: list[str], i: int, *, gefaltet: bool) -> tuple[str, int]:
    gesammelt: list[str] = []
    einzug: int | None = None
    while i < len(zeilen):
        zeile = zeilen[i]
        if not zeile.strip():
            if einzug is None:
                i += 1
                continue
            # Leerzeile beendet den Block nur, wenn danach nichts Eingeruecktes folgt.
            rest = zeilen[i + 1:]
            naechste = next((z for z in rest if z.strip()), None)
            if naechste is None or len(naechste) - len(naechste.lstrip(" ")) < einzug:
                break
            gesammelt.append("")
            i += 1
            continue
        breite = len(zeile) - len(zeile.lstrip(" "))
        if einzug is None:
            if breite == 0:
                break
            einzug = breite
        if breite < einzug:
            break
        gesammelt.append(zeile[einzug:])
        i += 1
    while gesammelt and not gesammelt[-1]:
        gesammelt.pop()
    if not gefaltet:
        return "\n".join(gesammelt), i
    absaetze: list[list[str]] = [[]]
    for zeile in gesammelt:
        if zeile:
            absaetze[-1].append(zeile)
        elif absaetze[-1]:
            absaetze.append([])
    return "\n\n".join(" ".join(a) for a in absaetze if a), i


# --------------------------------------------------------------------------
# Belege
# --------------------------------------------------------------------------

_WARUM = re.compile(r"^\*\*Warum das folgt:\*\*\s*", re.M)


def _lies_belege(bib: Bibliothek, basis: Path, herkunft: str) -> None:
    ordner = basis / "belege"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("B-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        bid = str(kopf.get("id") or datei.stem)
        rumpf = _rumpf(datei)
        teile = _WARUM.split(rumpf, maxsplit=1)
        aussage = _entwirre(teile[0])
        begruendung = _entwirre(teile[1]) if len(teile) > 1 else ""
        if not kopf.get("fundstelle"):
            bib.melde(
                "beleg_ohne_fundstelle",
                "fehler",
                bid,
                f"BIB-7: {_rel(bib, datei)} nennt keine Fundstelle.",
            )
        _verdraengt(bib, bib.belege, bid, herkunft, "Beleg", datei)
        bib.belege[bid] = Beleg(
            id=bid,
            fundstelle_id=_text(kopf.get("fundstelle")),
            gilt_ab=_text(kopf.get("gilt_ab")),
            zuversicht=_text(kopf.get("zuversicht")),
            aussage=aussage,
            begruendung=begruendung,
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )


# --------------------------------------------------------------------------
# Wissenseinheiten
# --------------------------------------------------------------------------

_WE_ABSCHNITT = re.compile(r"^##\s+(.+?)\s*$", re.M)


def _lies_einheiten(bib: Bibliothek, basis: Path, herkunft: str) -> None:
    ordner = basis / "einheiten"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("WE-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        wid = str(kopf.get("id") or datei.stem)
        teile = _abschnitte(_rumpf(datei))
        if not kopf.get("belegt_durch"):
            bib.melde(
                "einheit_ohne_beleg",
                "fehler",
                wid,
                f"BIB-11: {_rel(bib, datei)} nennt keine Belege.",
            )
        _verdraengt(bib, bib.einheiten, wid, herkunft, "Wissenseinheit", datei)
        stichwort = _text(kopf.get("stichwort"))
        if not stichwort:
            bib.melde(
                "einheit_ohne_stichwort",
                "hinweis",
                wid,
                f"MMP-3: {_rel(bib, datei)} hat kein Stichwort. In der Mindmap "
                "steht dann der Titel, und der ist ein Satz.",
            )
        elif len(stichwort.split()) > 4:
            bib.melde(
                "stichwort_zu_lang",
                "fehler",
                wid,
                "MMP-3: Stichwort %r hat %d Woerter, erlaubt sind hoechstens vier."
                % (stichwort, len(stichwort.split())),
            )
        # BIB-11: Eine inhaltliche Aussage ohne Beleg gehoert als Einordnung
        # gekennzeichnet (`[E]`). Jeder Absatz des Inhalts ist ein Folienpunkt
        # (siehe dienst/folie.py), also faellt ein unmarkierter Absatz auf der
        # Folie als Punkt ohne Herkunft an.
        #
        # **Warum das hier gemeldet wird und nicht stillschweigend passiert.**
        # `folie.py` setzt fuer solche Absaetze `art: unbelegt` und schreibt
        # dazu, das sei „ein Mangel am Material — er wird sichtbar gemacht,
        # nicht geglaettet". Gezaehlt hat ihn bis zum 13.09.2026 niemand:
        # 270 Absaetze in der Bibliothek sind unmarkiert, und die App hat sie
        # wie belegte gezeichnet (OBF-17 verlangt das Gegenteil).
        #
        # Kein `fehler`, sondern `abweichung`: Die Absaetze sind nicht falsch,
        # sie sind ungekennzeichnet. Wer sie pauschal zu `[E]` erklaert, kann
        # eine unbelegte **Behauptung** als Einordnung tarnen — das ist genau
        # der Weg, den TB-1 verstellt. Deshalb zaehlt es, statt zu raten.
        for absatz in _ABSATZ_INHALT.split(teile.get("Inhalt", "")):
            a = absatz.strip()
            if not a or a.startswith(("#", "|", "- ", "* ", ">")):
                continue
            if "[E]" in a or _BELEG_IM_TEXT.search(a):
                continue
            bib.melde(
                "absatz_ohne_marker",
                "abweichung",
                wid,
                "BIB-11: Ein Absatz traegt weder Beleg noch [E] und wird auf "
                "der Folie zu einem Punkt ohne Herkunft: %r"
                % (a[:90] + ("…" if len(a) > 90 else "")),
            )

        bib.einheiten[wid] = Wissenseinheit(
            id=wid,
            titel=_text(kopf.get("titel")),
            grad=_text(kopf.get("grad")),
            stichwort=stichwort,
            belegt_durch=_liste(kopf.get("belegt_durch")),
            setzt_voraus=_liste(kopf.get("setzt_voraus")),
            widerspricht=_liste(kopf.get("widerspricht")),
            siehe_auch=_liste(kopf.get("siehe_auch")),
            gilt_ab=_text(kopf.get("gilt_ab")),
            kurzfassung=_entwirre(teile.get("Kurzfassung", "")),
            # Der Inhalt behaelt seine Absaetze: Sie sind die Folienpunkte
            # (siehe dienst/folie.py), nicht nur Satzumbruch.
            inhalt=teile.get("Inhalt", ""),
            prueffrage=_entwirre(teile.get("Prüffrage", teile.get("Prueffrage", ""))),
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )


def _lies_kapitel(bib: Bibliothek, wurzel: Path) -> None:
    """Liest ``kapitel/K-*.md``.

    Ohne Kapiteldatei gibt es kein Kapitel — und damit weder Mindmap noch
    Gespraechspartner. Das ist gewollt: Welche Lektionen zusammengehoeren,
    entscheidet der Mensch, nicht eine Heuristik ueber Abschnittsbuchstaben
    (BIB-16).
    """
    ordner = wurzel / "kapitel"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("K-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        kid = _text(kopf.get("id")) or datei.stem
        pfad_id = _text(kopf.get("pfad"))
        lektionen = [str(x) for x in (kopf.get("lektionen") or [])]
        if pfad_id and pfad_id not in bib.pfade:
            bib.melde("kapitel_ohne_lernpfad", "fehler", kid,
                      f"{_rel(bib, datei)} nennt Lernpfad {pfad_id}; den gibt es nicht.")
        else:
            bekannt = {a.schluessel for a in bib.pfade[pfad_id].abschnitte} if pfad_id else set()
            for schluessel in lektionen:
                if schluessel not in bekannt:
                    bib.melde("lektion_ohne_abschnitt", "fehler", kid,
                              f"{kid} nennt Lektion {schluessel}; der Lernpfad "
                              f"{pfad_id} kennt keinen solchen Abschnitt.")
        bib.kapitel[kid] = Kapitel(
            id=kid,
            pfad_id=pfad_id,
            nummer=_ganzzahl(bib, kid, "nummer", kopf.get("nummer"), datei) or 1,
            titel=_text(kopf.get("titel")),
            kurzfassung=_entwirre(_text(kopf.get("kurzfassung"))),
            lektionen=lektionen,
            pfad=_rel(bib, datei),
        )


def _lies_mindmaps(bib: Bibliothek, basis: Path, herkunft: str) -> None:
    """Liest ``mindmap/<Kapitel>.md`` — die Strukturanalyse je Kapitel.

    Fehlt sie, ist das kein Fehler: Ein Kapitel ohne Analyse bekommt keine
    Achsen, und die Ansicht sagt das selbst. Erfunden wird hier nichts.
    """
    # **Die Analyse gehoert dem Kapitel, nicht einem Lauf.** Bis zum
    # 12.09.2026 lag sie in `eingang/M-001/mindmap/`, also im Ordner eines
    # Modellierlaufs. Damit war sie an ein Material gebunden, das mit ihr
    # nichts zu tun hat — und ein Auftrag fuer K-02 analysierte K-01.
    ordner = basis / "mindmap"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("K-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        kapitel = _text(kopf.get("kapitel")) or datei.stem
        achsen: list[Mindmapachse] = []
        gesehen: dict[str, str] = {}
        # **Zwei Ebenen bleiben zwei Ebenen** (MMP-10a). Die Analyse zu K-01
        # braucht sie: Bei dreizehn Lektionen traegt eine flache Liste nicht,
        # deshalb gliedert sie in neun Achsen mit Unterachsen.
        #
        # Bis zum 13.09.2026 wurde die obere Ebene hier **weggeworfen** und
        # die untere zur ersten gemacht, weil der Renderer nur eine Ebene
        # konnte. Das Ergebnis waren 39 gleichrangige Fragen an einer Wurzel —
        # also genau die Stichpunktliste, gegen die E-24 geschrieben wurde.
        # Der Renderer zeichnet `kinder` rekursiv und kann es laengst; nur
        # diese Stelle hat es nicht weitergegeben.
        #
        # Die Zuordnung bleibt an der Unterachse (dort stehen die Einheiten),
        # die Elternachse kommt als `eltern` mit. Wer sie ignoriert, bekommt
        # wieder die flache Liste — das ist der Rueckfall, nicht der Normalfall.
        flach: list[dict] = []
        for roh in kopf.get("achsen") or []:
            if not isinstance(roh, dict):
                continue
            unter = [u for u in (roh.get("unterachsen") or []) if isinstance(u, dict)]
            if unter:
                for u in unter:
                    flach.append({
                        "id": _text(u.get("id")),
                        "frage": _text(u.get("frage")) or _text(roh.get("frage")),
                        "einheiten": u.get("einheiten"),
                        "eltern": _text(roh.get("id")),
                        "eltern_frage": _text(roh.get("frage")),
                    })
            else:
                flach.append(roh)

        for roh in flach:
            frage = _text(roh.get("frage"))
            aid = _text(roh.get("id")) or f"A{len(achsen) + 1}"
            if frage and not frage.endswith("?"):
                bib.melde(
                    "achse_ist_keine_frage",
                    "hinweis",
                    f"{kapitel}/{aid}",
                    "Eine Achse sagt, wonach sortiert wurde: %r ist keine Frage."
                    % frage,
                )
            mitglieder = _liste(roh.get("einheiten"))
            for wid in mitglieder:
                if wid in gesehen:
                    # Haengt eine Einheit an zwei Achsen, ist die Gliederung
                    # falsch gewaehlt. Querbezuege zeigt MMP-5 getrennt.
                    bib.melde(
                        "einheit_an_zwei_achsen",
                        "fehler",
                        wid,
                        "%s haengt an %s und an %s." % (wid, gesehen[wid], aid),
                    )
                gesehen[wid] = aid
            achsen.append(Mindmapachse(
                id=aid, frage=frage, einheiten=mitglieder,
                eltern=_text(roh.get("eltern")) or None,
                eltern_frage=_text(roh.get("eltern_frage")) or None))

        teile = _abschnitte(_rumpf(datei))
        _verdraengt(bib, bib.mindmaps, kapitel, herkunft, "Mindmap-Analyse", datei)
        bib.mindmaps[kapitel] = Mindmapanalyse(
            kapitel=kapitel,
            kern=_text(kopf.get("kern")),
            achsen=achsen,
            kernaussage=_entwirre(teile.get("Kernaussage", "")),
            beziehungen=_entwirre(teile.get("Beziehungen", "")),
            layout=_entwirre(teile.get("Layout", "")),
            pfad=_rel(bib, datei),
            bild=_text(kopf.get("bild")) or None,
            bild_breite=_ganzzahl(bib, kapitel, "bild_breite", kopf.get("bild_breite"), datei),
            bild_hoehe=_ganzzahl(bib, kapitel, "bild_hoehe", kopf.get("bild_hoehe"), datei),
            bild_titel=_text(kopf.get("bild_titel")) or None,
            bild_belege=list(kopf.get("bild_belege") or []),
        )


def _abschnitte(rumpf: str) -> dict[str, str]:
    ergebnis: dict[str, str] = {}
    marken = list(_WE_ABSCHNITT.finditer(rumpf))
    for nr, marke in enumerate(marken):
        ende = marken[nr + 1].start() if nr + 1 < len(marken) else len(rumpf)
        ergebnis[marke.group(1)] = rumpf[marke.end():ende].strip()
    return ergebnis


# --------------------------------------------------------------------------
# Lektionen (BIB-26, BIB-27)
# --------------------------------------------------------------------------

_MARKEN_ABSCHNITT = re.compile(r"^##\s+Kapitelmarken\s*$", re.M)
_MARKEN_ZEILE = re.compile(r"^\|(?P<zeit>[^|]+)\|(?P<titel>[^|]+)\|(?P<art>[^|]+)\|\s*$", re.M)
_TRENNZEILE = re.compile(r"^[\s:|-]+$")
_ZEIT = re.compile(r"^(?:(\d+):)?(\d{1,2}):(\d{2})$")


def _lies_lektionen(bib: Bibliothek, basis: Path, herkunft: str) -> None:
    ordner = basis / "lektionen"
    if not ordner.is_dir():
        return
    for datei in sorted(ordner.glob("L-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        lid = str(kopf.get("id") or datei.stem)

        fehlend = [
            k
            for k in ("kapitel", "nummer", "titel", "dauer_sek", "wissenseinheiten", "audio")
            if not kopf.get(k)
        ]
        if fehlend:
            bib.melde(
                "lektion_unvollstaendig",
                "abweichung",
                lid,
                "BIB-26/27 verlangen eine Lektion mit Kapitel, Nummer, Titel, Dauer, "
                "ihren Wissenseinheiten und ihrem Audio; es fehlen: " + ", ".join(fehlend),
            )

        einheiten = _liste(kopf.get("wissenseinheiten"))
        doppelt = [w for w in einheiten if einheiten.count(w) > 1]
        if doppelt:
            bib.melde(
                "lektion_einheit_doppelt",
                "abweichung",
                lid,
                f"{_rel(bib, datei)} nennt {', '.join(sorted(set(doppelt)))} mehrfach. "
                "BIB-27 kennt eine Reihenfolge, keine Wiederholung — die Stelle bleibt "
                "stehen, wie sie dasteht, und die Position ist die erste.",
            )

        marken = _lies_kapitelmarken(bib, lid, datei, _rumpf(datei))
        stimmen = kopf.get("stimmen")

        _verdraengt(bib, bib.lektionen, lid, herkunft, "Lektion", datei)
        bib.lektionen[lid] = Lektion(
            id=lid,
            kapitel=_text(kopf.get("kapitel")),
            abschnitt=_text(kopf.get("abschnitt")),
            nummer=_ganzzahl(bib, lid, "nummer", kopf.get("nummer"), datei),
            titel=_text(kopf.get("titel")),
            dauer_sek=_ganzzahl(bib, lid, "dauer_sek", kopf.get("dauer_sek"), datei),
            wissenseinheiten=list(dict.fromkeys(einheiten)),
            audio=_text(kopf.get("audio")),
            auftrag=_text(kopf.get("auftrag")),
            zeichen_vertont=_ganzzahl(
                bib, lid, "zeichen_vertont", kopf.get("zeichen_vertont"), datei
            ),
            stimmen=dict(stimmen) if isinstance(stimmen, dict) else {},
            erzeugt=_text(kopf.get("erzeugt")),
            pipeline=_ganzzahl(bib, lid, "pipeline", kopf.get("pipeline"), datei),
            kapitelmarken=marken,
            bild=_text(kopf.get("bild")) or None,
            bild_breite=_ganzzahl(bib, lid, "bild_breite", kopf.get("bild_breite"), datei),
            bild_hoehe=_ganzzahl(bib, lid, "bild_hoehe", kopf.get("bild_hoehe"), datei),
            bild_titel=_text(kopf.get("bild_titel")) or None,
            bild_belege=list(kopf.get("bild_belege") or []),
            pfad_id="",
            herkunft=herkunft,
            pfad=_rel(bib, datei),
        )


def _lies_kapitelmarken(
    bib: Bibliothek, lid: str, datei: Path, rumpf: str
) -> list[Kapitelmarke]:
    """Die Marken stehen als Tabelle im Fliesztext, nicht im Frontmatter.

    Das ist die Form, die der Podcastlauf abgelegt hat. Gelesen wird nur der
    Abschnitt ``## Kapitelmarken`` — eine andere Dreispaltentabelle in
    derselben Datei (etwa unter „Herkunft") ist keine Marke.
    """
    anfang = _MARKEN_ABSCHNITT.search(rumpf)
    if anfang is None:
        bib.melde(
            "lektion_ohne_kapitelmarken",
            "abweichung",
            lid,
            f"R-10 sieht Kapitelmarken mit 'art' vor. {_rel(bib, datei)} hat keinen "
            "Abschnitt '## Kapitelmarken'; der Dienst liefert eine leere Liste statt "
            "aus der Dauer Marken zu rechnen.",
        )
        return []
    naechster = re.compile(r"^##\s+", re.M).search(rumpf, anfang.end())
    block = rumpf[anfang.end(): naechster.start() if naechster else len(rumpf)]

    marken: list[Kapitelmarke] = []
    for treffer in _MARKEN_ZEILE.finditer(block):
        zeit = treffer.group("zeit").strip()
        titel = _saeubere(treffer.group("titel"))
        art = _saeubere(treffer.group("art")).lower()
        if _TRENNZEILE.match(treffer.group(0).strip()):
            continue
        sek = _sekunden(zeit)
        if sek is None:
            # Die Kopfzeile ('| Zeit | Abschnitt | Art |') faellt hier heraus,
            # ohne sie an der Position zu erkennen — eine Kopfzeile ist genau
            # die Zeile, deren erste Spalte keine Zeitangabe ist.
            if zeit.lower() not in ("zeit", "zeitmarke"):
                bib.melde(
                    "kapitelmarke_ohne_zeit",
                    "abweichung",
                    lid,
                    f"{_rel(bib, datei)}: '{zeit}' ist keine Zeitangabe (m:ss oder "
                    "h:mm:ss). Die Zeile wird nicht als Marke gelesen.",
                )
            continue
        if art not in MARKEN_ARTEN:
            bib.melde(
                "kapitelmarke_fremde_art",
                "abweichung",
                lid,
                f"R-10 kennt {', '.join(sorted(MARKEN_ARTEN))}. {_rel(bib, datei)} "
                f"fuehrt bei '{titel}' die Art '{art}'. Sie wird unveraendert "
                "ausgegeben statt auf eine bekannte umgedeutet.",
            )
        marken.append(Kapitelmarke(sek=sek, titel=titel, art=art))

    if not marken:
        bib.melde(
            "lektion_ohne_kapitelmarken",
            "abweichung",
            lid,
            f"{_rel(bib, datei)} hat einen Abschnitt '## Kapitelmarken', darin steht "
            "aber keine lesbare Marke.",
        )
        return []
    if [m.sek for m in marken] != sorted(m.sek for m in marken):
        bib.melde(
            "kapitelmarken_unsortiert",
            "abweichung",
            lid,
            f"{_rel(bib, datei)}: die Marken stehen nicht in aufsteigender Zeit. Sie "
            "werden in der Reihenfolge der Datei ausgegeben — umsortieren hiesze "
            "entscheiden, welche der beiden Angaben stimmt.",
        )
    return marken


def _sekunden(zeit: str) -> int | None:
    treffer = _ZEIT.match(zeit.strip())
    if not treffer:
        return None
    stunden, minuten, sekunden = treffer.groups()
    return int(stunden or 0) * 3600 + int(minuten) * 60 + int(sekunden)


def _ganzzahl(bib: Bibliothek, betrifft: str, feld: str, wert: object, datei: Path) -> int | None:
    """Frontmatter-Skalare sind Text (siehe ``yaml_min._skalar``).

    Was keine Zahl ist, wird ``None`` und gemeldet — nicht auf 0 gesetzt. Eine
    Dauer 0 waere eine Aussage, die niemand getroffen hat, und sie faerbt ueber
    ``gehoert_anteil`` bis in den Lernstand durch.
    """
    if wert is None or _text(wert) == "":
        return None
    try:
        return int(_text(wert))
    except ValueError:
        bib.melde(
            "zahl_unlesbar",
            "abweichung",
            betrifft,
            f"{_rel(bib, datei)}: {feld} ist '{_text(wert)}' und keine ganze Zahl. "
            "Das Feld bleibt leer, statt eine Zahl zu erfinden.",
        )
        return None


# Abschnittsschluessel duerfen mehr als ein Zeichen haben. P-01 nutzt A bis M,
# weil dreizehn Buchstaben reichten. P-02 hat rund achtzig Lektionen ueber zehn
# Kapitel; dort tragen die Schluessel ihr Kapitel mit (H1, S4, G7), und das ist
# beim Lesen einer Belegliste mehr wert als Alphabetreihenfolge.
_PFAD_ABSCHNITT = re.compile(r"^###\s+([A-Z][A-Z0-9-]*)\s+[—-]\s+(.+?)\s*$", re.M)
_TABELLENZEILE = re.compile(r"^\|\s*([A-Z][A-Z0-9-]*)\s*\|(.+?)\|(.+?)\|\s*$", re.M)


def _ordne_lektionen_zu(bib: Bibliothek) -> None:
    """Findet zu jeder Lektion ihren Lernpfad ueber ihr Kapitel.

    Bis zum 12.09.2026 lief das ueber den Abschnittsbuchstaben und war
    mehrdeutig, sobald zwei Lernpfade denselben Buchstaben fuehren. Seit es
    Kapitel-IDs gibt (BIB-26), ist es abgelesen statt erschlossen.
    """
    for lektion in bib.lektionen.values():
        kapitel = bib.kapitel.get(lektion.kapitel)
        if kapitel is None:
            bib.melde(
                "lektion_kapitel_unbekannt",
                "fehler",
                lektion.id,
                f"{lektion.pfad} nennt Kapitel '{lektion.kapitel}'. In kapitel/ "
                "gibt es kein solches.",
            )
            continue
        lektion.pfad_id = kapitel.pfad_id
        if lektion.abschnitt and lektion.abschnitt not in kapitel.lektionen:
            bib.melde(
                "lektion_ausserhalb_des_kapitels",
                "fehler",
                lektion.id,
                f"{lektion.id} nennt Abschnitt '{lektion.abschnitt}'; {kapitel.id} "
                "fuehrt ihn nicht.",
            )

def _lies_pfade(bib: Bibliothek, wurzel: Path) -> None:
    ordner = wurzel / "pfade"
    if not ordner.is_dir():
        bib.melde("pfade_fehlen", "fehler", "-", "Es gibt keinen Ordner pfade/")
        return
    for datei in sorted(ordner.glob("P-*.md")):
        kopf = _kopf(bib, datei)
        if kopf is None:
            continue
        pid = str(kopf.get("id") or datei.stem)
        rumpf = _rumpf(datei)

        kerne = {
            m.group(1): _saeubere(m.group(3))
            for m in _TABELLENZEILE.finditer(rumpf)
        }
        abschnitte: list[Abschnitt] = []
        marken = list(_PFAD_ABSCHNITT.finditer(rumpf))
        for nr, marke in enumerate(marken):
            ende = marken[nr + 1].start() if nr + 1 < len(marken) else len(rumpf)
            schluessel = marke.group(1)
            abschnitte.append(
                Abschnitt(
                    schluessel=schluessel,
                    nummer=nr + 1,
                    titel=_saeubere(marke.group(2)),
                    kern=kerne.get(schluessel, ""),
                    text=rumpf[marke.end():ende].strip(),
                )
            )
        if not abschnitte:
            bib.melde(
                "pfad_ohne_abschnitte",
                "fehler",
                pid,
                f"{_rel(bib, datei)}: keine '### X — …'-Abschnitte gefunden.",
            )
        bib.pfade[pid] = Lernpfad(
            id=pid,
            titel=_text(kopf.get("titel")),
            kurzfassung=_text(kopf.get("kurzfassung")),
            status=_text(kopf.get("status")),
            sprache=_text(kopf.get("sprache")),
            abschnitte=abschnitte,
            kopf=kopf,
            pfad=_rel(bib, datei),
            reihenfolge=_ganzzahl(bib, pid, "reihenfolge", kopf.get("reihenfolge"), datei) or 99,
        )
        bib.melde(
            "kapitelschicht_ohne_id",
            "abweichung",
            pid,
            f"BIB-26 sieht Kapitel mit 'K-'-IDs vor. {_rel(bib, datei)} fuehrt "
            f"{len(abschnitte)} Abschnitte, die nur durch Buchstaben (A…) "
            "bezeichnet sind. Der Dienst gibt den Buchstaben als Kapitel-ID aus "
            "und vergibt keine K-Nummern — das gehoert dem Menschen (BIB-16/29).",
        )


# --------------------------------------------------------------------------
# Zusammenhangspruefung
# --------------------------------------------------------------------------


def _pruefe_zusammenhang(bib: Bibliothek) -> None:
    for beleg in bib.belege.values():
        if beleg.fundstelle_id and beleg.fundstelle_id not in bib.fundstellen:
            bib.melde(
                "fundstelle_unbekannt",
                "fehler",
                beleg.id,
                f"{beleg.pfad} verweist auf {beleg.fundstelle_id}, die es nicht gibt.",
            )
    for fs in bib.fundstellen.values():
        if fs.version_id and f"{fs.quelle_id}/{fs.version_id}" not in bib.versionen:
            bib.melde(
                "version_unbekannt",
                "abweichung",
                fs.id,
                f"BIB-4a: {fs.id} zeigt auf Version {fs.version_id}, die nicht "
                f"unter quellen/{fs.quelle_id}/versionen/ liegt.",
            )

    namen = {v.id for v in bib.versionen.values()}
    if bib.versionen and len(namen) < len(bib.versionen):
        bib.melde(
            "versions_id_nicht_global",
            "abweichung",
            "quellen/*/versionen/",
            f"BIB-4a spricht von einer Quellenversion mit eigener ID. Im Material "
            f"tragen {len(bib.versionen)} Versionsdateien nur {len(namen)} "
            f"verschiedene Namen ({', '.join(sorted(namen))}) — der Name ist das "
            "Abrufdatum und nur innerhalb einer Quelle eindeutig. Der Index "
            "schluesselt deshalb auf '<Quelle>/<Version>'.",
        )
    for we in bib.einheiten.values():
        for bid in we.belegt_durch:
            if bid not in bib.belege:
                bib.melde(
                    "beleg_unbekannt",
                    "fehler",
                    we.id,
                    f"{we.pfad} nennt Beleg {bid}, den es nicht gibt.",
                )
        for feld, ziele in (
            ("setzt_voraus", we.setzt_voraus),
            ("widerspricht", we.widerspricht),
            ("siehe_auch", we.siehe_auch),
        ):
            for ziel in ziele:
                if ziel not in bib.einheiten:
                    bib.melde(
                        "einheit_unbekannt",
                        "fehler",
                        we.id,
                        f"{we.pfad}: {feld} nennt {ziel}, das es nicht gibt.",
                    )

    if bib.einheiten and not any(
        we.herkunft == FREIGEGEBEN for we in bib.einheiten.values()
    ):
        bib.melde(
            "nichts_freigegeben",
            "hinweis",
            "einheiten/",
            f"{len(bib.einheiten)} Wissenseinheiten liegen alle im Eingang und "
            "sind nach BIB-16 nicht freigegeben. Der Dienst liefert sie aus und "
            "kennzeichnet sie als 'eingang'.",
        )

    if bib.einheiten and any(we.siehe_auch for we in bib.einheiten.values()):
        bib.melde(
            "kantentyp_ausserhalb_bib22",
            "abweichung",
            "einheiten/",
            "Das Frontmatter fuehrt 'siehe_auch'. BIB-22 kennt diesen Typ nicht "
            "(stuetzt, widerspricht, praezisiert, ersetzt, handelt_von, "
            "setzt_voraus, dient_lernziel, prueft). Die Kante wird mit dem Typ "
            "'siehe_auch' indiziert und hier gemeldet, statt sie auf einen "
            "BIB-22-Typ umzudeuten.",
        )

    lange_titel = [we.id for we in bib.einheiten.values() if len(we.titel) > 40]
    if lange_titel:
        bib.melde(
            "titel_ist_satz",
            "abweichung",
            ", ".join(lange_titel[:3]) + (" …" if len(lange_titel) > 3 else ""),
            f"MMP-3 verlangt am Mindmap-Knoten ein Stichwort, keinen Satz. "
            f"{len(lange_titel)} von {len(bib.einheiten)} Einheiten tragen als "
            "Titel einen vollstaendigen Satz (der Modellierer hat die Kernaussage "
            "in den Titel gelegt). Der Dienst gibt den Titel unveraendert als "
            "'label' aus — ein gekuerztes Stichwort waere erfunden.",
        )

    if bib.einheiten:
        bib.melde(
            "strittig_ohne_feld",
            "abweichung",
            "einheiten/",
            "Der Datenvertrag kennt am Mindmap-Knoten ein 'strittig: true'. Im "
            "Frontmatter gibt es kein solches Feld; Strittigkeit steht im "
            "Fliesztext (etwa WE-0004 zum Verbosity Bias). Der Dienst setzt das "
            "Merkmal deshalb nicht — geraten waere es falsch in beide Richtungen.",
        )

    _pruefe_lektionen(bib)


def _pruefe_lektionen(bib: Bibliothek) -> None:
    """BIB-26/27 gegen das Material.

    Bis zum 11.09.2026 stand hier ein einziger Befund: die Schicht fehlt ganz.
    Seit ``eingang/M-001/lektionen/L-F01.md`` ist die Frage eine andere — nicht
    mehr *gibt es Lektionen*, sondern *welches Kapitel hat noch keine*.
    """
    if bib.einheiten and not bib.lektionen:
        bib.melde(
            "lektionsschicht_fehlt",
            "abweichung",
            "-",
            "BIB-26/27 verlangen eine Lektion, die ihre Wissenseinheiten nennt. "
            "Im Material gibt es keine Lektionsdatei (lektionen/L-*.md). Damit "
            "sind /api/lektion/… und die Kapitel-Mindmap ohne Inhalt.",
        )
        return

    for lektion in bib.lektionen.values():
        if not lektion.wissenseinheiten:
            bib.melde(
                "lektion_ohne_einheiten",
                "fehler",
                lektion.id,
                f"BIB-27: {lektion.pfad} nennt keine Wissenseinheiten. Eine Lektion, "
                "die nicht sagt, woraus sie besteht, ist nicht auf die Bibliothek "
                "zurueckfuehrbar.",
            )
        for wid in lektion.wissenseinheiten:
            if wid not in bib.einheiten:
                bib.melde(
                    "lektion_einheit_unbekannt",
                    "fehler",
                    lektion.id,
                    f"{lektion.pfad} nennt {wid}, das es in einheiten/ nicht gibt.",
                )

    # Die Umkehrung: Einheiten, die in keiner Lektion vorkommen. Kein Fehler —
    # sie sind recherchiert, aber noch nicht vertont (AUF-10: einzeln).
    verwendet = {w for l in bib.lektionen.values() for w in l.wissenseinheiten}
    unvertont = sorted(set(bib.einheiten) - verwendet)
    if unvertont:
        bib.melde(
            "einheit_ohne_lektion",
            "hinweis",
            ", ".join(unvertont[:3]) + (" …" if len(unvertont) > 3 else ""),
            f"{len(unvertont)} von {len(bib.einheiten)} Wissenseinheiten kommen in "
            "keiner Lektion vor. Das ist kein Mangel an der Bibliothek, sondern der "
            "Stand der Vertonung: Erzeugungsauftraege laufen einzeln (AUF-10).",
        )

    # Der Befund, der 'lektionsschicht_fehlt' abloest: nicht ob es Lektionen
    # gibt, sondern welches Kapitel noch keine hat.
    belegt: dict[tuple[str, str], int] = {}
    for lektion in bib.lektionen.values():
        if lektion.pfad_id:
            schluessel = (lektion.pfad_id, lektion.kapitel)
            belegt[schluessel] = belegt.get(schluessel, 0) + 1
    for pfad in bib.pfade.values():
        leer = [a.schluessel for a in pfad.abschnitte if (pfad.id, a.schluessel) not in belegt]
        if not leer:
            continue
        bib.melde(
            "kapitel_ohne_lektion",
            "abweichung",
            pfad.id,
            f"{len(leer)} von {len(pfad.abschnitte)} Kapiteln in {pfad.pfad} haben "
            f"keine Lektion: {', '.join(leer)}. Der Dienst gibt sie mit leerer "
            "Lektionsliste aus; 'hat_mindmap' ist dort false, weil es ohne Lektion "
            "auch keine Zuordnung Einheit → Kapitel gibt (BIB-27).",
        )

    for lektion in bib.lektionen.values():
        if lektion.nummer is None:
            continue
        geschwister = sorted(
            l.nummer
            for l in bib.lektionen.values()
            if l.pfad_id == lektion.pfad_id and l.kapitel == lektion.kapitel
            and l.nummer is not None
        )
        if len(geschwister) != len(set(geschwister)):
            bib.melde(
                "lektionsnummer_doppelt",
                "abweichung",
                f"{lektion.pfad_id}/{lektion.kapitel}",
                f"In Kapitel {lektion.kapitel} tragen zwei Lektionen dieselbe Nummer. "
                "Der Dienst sortiert nach Nummer und dann nach ID; welche zuerst "
                "gehoert werden soll, sagt das Material nicht.",
            )
            break


# --------------------------------------------------------------------------
# Hilfen
# --------------------------------------------------------------------------


def _kopf(bib: Bibliothek, datei: Path) -> dict[str, object] | None:
    text = datei.read_text(encoding="utf-8")
    block, _ = trenne_frontmatter(text)
    if block is None:
        bib.melde(
            "kein_frontmatter",
            "fehler",
            datei.stem,
            f"{_rel(bib, datei)} hat kein YAML-Frontmatter (BIB-18).",
        )
        return None
    try:
        return lies_block(block, herkunft=_rel(bib, datei))
    except YamlFehler as fehler:
        bib.melde("frontmatter_unlesbar", "fehler", datei.stem, str(fehler))
        return None


def _rumpf(datei: Path) -> str:
    _, rumpf = trenne_frontmatter(datei.read_text(encoding="utf-8"))
    return rumpf.strip()


def _rel(bib: Bibliothek, pfad: Path) -> str:
    try:
        return str(Path(pfad).resolve().relative_to(Path(bib.wurzel)))
    except ValueError:
        return str(pfad)


def _text(wert: object) -> str:
    if wert is None:
        return ""
    if isinstance(wert, list):
        return ", ".join(str(w) for w in wert)
    return str(wert).strip()


def _entwirre(text: str) -> str:
    """Loest den harten Zeilenumbruch des Markdown-Flieszsatzes auf.

    Die Dateien sind auf ~78 Zeichen umgebrochen. Der Umbruch gehoert der
    Datei, nicht dem Satz — wer ihn mitliefert, zwingt jeder Oberflaeche die
    Spaltenbreite eines Texteditors auf. Absatzgrenzen (Leerzeilen) bleiben.
    """
    absaetze = re.split(r"\n\s*\n", text.strip())
    return "\n\n".join(" ".join(a.split()) for a in absaetze if a.strip())


def _liste(wert: object) -> list[str]:
    if wert is None:
        return []
    if isinstance(wert, list):
        return [str(w).strip() for w in wert if str(w).strip()]
    text = str(wert).strip()
    return [text] if text else []


def _saeubere(text: str) -> str:
    """Nimmt die Markdown-Auszeichnung aus einer Ueberschrift oder Tabellenzelle.

    Nur ``**`` — mehr steht dort nicht, und was nicht vorkommt, wird auch
    nicht behandelt.
    """
    return text.replace("**", "").strip()


def _verdraengt(
    bib: Bibliothek,
    bestand: dict[str, object],
    kennung: str,
    herkunft: str,
    art: str,
    datei: Path,
) -> None:
    alt = bestand.get(kennung)
    if alt is None:
        return
    alte_herkunft = getattr(alt, "herkunft", "?")
    alter_pfad = getattr(alt, "pfad", "?")
    bib.melde(
        "id_doppelt",
        "abweichung",
        kennung,
        f"{art} {kennung} kommt zweimal vor: {alter_pfad} ({alte_herkunft}) und "
        f"{_rel(bib, datei)} ({herkunft}). Es gilt der spaetere Auftrag "
        f"({herkunft}); Freigegebenes gilt immer.",
    )
