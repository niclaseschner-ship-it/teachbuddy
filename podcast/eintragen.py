"""Trägt eine gebaute Folge in ihre Lektion ein.

**Der Schritt, der gefehlt hat.** Am 12.09.2026 lagen vier vertonte Folgen im
Arbeitsverzeichnis, und alle vier Lektionen sagten weiter `dauer_sek: 600` und
nannten keine Tondatei. In der App hiess das: jede Lektion genau 10:00 lang,
keine spielt. Gebaut war alles, eingetragen nichts.

`dauer_sek: 600` ist die **geplante** Dauer nach BIB-26, die der Modellierer
schreibt, bevor es eine Folge gibt. Sobald die Folge da ist, gilt die
**gemessene**. Zwei Wahrheiten für dieselbe Zahl laufen immer auseinander
(R-1), und hier war die falsche die sichtbare.

Aufruf::

    python3 -m podcast.eintragen <lektion.md> <arbeitsverzeichnis-der-folge>
    python3 -m podcast.eintragen --alle      # jede Lektion zu ihrer Folge
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import pfade

WISSEN = pfade.WISSEN
ARBEIT = pfade.PODCAST_ARBEIT


def mmss(sek: float) -> str:
    return f"{int(sek) // 60}:{int(sek) % 60:02d}"


def _setze(kopf: str, feld: str, wert: str) -> str:
    """Ein Kopffeld setzen oder anlegen, ohne die übrigen anzufassen."""
    zeile = f"{feld}: {wert}"
    if re.search(rf"^{feld}:.*$", kopf, re.M):
        return re.sub(rf"^{feld}:.*$", zeile, kopf, count=1, flags=re.M)
    return kopf.rstrip("\n") + "\n" + zeile + "\n"


def passt(lektion: Path, ordner: Path) -> str | None:
    """Gehoert diese Folge wirklich zu dieser Lektion? Gibt den Grund zurueck,
    wenn nicht.

    **Warum das geprueft werden muss.** Am 12.09.2026 wurde Kapitel K-02 neu
    modelliert, und dabei verschoben sich die WE-Nummern. Der Abgleich lief
    ueber den Titel, und der stimmte weiter — also hing die Folge „Kontext ist
    der ganze Zustand" danach an einer Lektion, deren Einheiten voellig andere
    waren. Ein Titel ist keine Identitaet.

    Verglichen wird, woraus die Folge gebaut wurde (`auftrag.json`) mit dem,
    was die Lektion heute nennt.
    """
    auftrag = ordner / "auftrag.json"
    if not auftrag.is_file():
        return "kein auftrag.json — woraus die Folge gebaut ist, steht nirgends"
    roh = json.loads(auftrag.read_text(encoding="utf-8"))
    gebaut = {e["id"] if isinstance(e, dict) else str(e)
              for e in (roh.get("einheiten") or roh.get("nur") or [])}
    m = re.search(r"^wissenseinheiten:\s*\[(.*?)\]\s*$",
                  lektion.read_text(encoding="utf-8"), re.M)
    verlangt = {x.strip() for x in (m.group(1) if m else "").split(",") if x.strip()}
    if not gebaut or not verlangt:
        return "Einheiten nicht vergleichbar"
    if gebaut != verlangt:
        fehlt = ", ".join(sorted(verlangt - gebaut)) or "—"
        zuviel = ", ".join(sorted(gebaut - verlangt)) or "—"
        return f"andere Einheiten (fehlt: {fehlt} · zuviel: {zuviel})"
    return None


def trage_ein(lektion: Path, ordner: Path) -> str:
    grund = passt(lektion, ordner)
    if grund:
        raise SystemExit(f"{lektion.name} ← {ordner.name}: {grund}")
    folge = json.loads((ordner / "folge.json").read_text(encoding="utf-8"))
    text = lektion.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        raise SystemExit(f"{lektion}: kein Frontmatter")
    kopf, rumpf = m.group(1), m.group(2)

    # Die fertige Folge wandert in die Bibliothek: Audio gehoert zur Lektion,
    # nicht zum Arbeitsordner, aus dem sie entstand.
    lid = re.search(r"^id:\s*(\S+)", kopf, re.M).group(1)
    ziel = WISSEN / "audio" / f"{lid}.mp3"
    ziel.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ordner / folge["audio"], ziel)
    rel = ziel.relative_to(WISSEN)
    alt_dauer = re.search(r"^dauer_sek:\s*(\d+)", kopf, re.M)
    kopf = _setze(kopf, "dauer_sek", str(int(folge["dauer_sek"])))
    kopf = _setze(kopf, "audio", str(rel))
    kopf = _setze(kopf, "auftrag", folge["id"])
    if folge.get("zeichen"):
        kopf = _setze(kopf, "zeichen_vertont", str(folge["zeichen"]))
    if folge.get("stimmen"):
        paare = ", ".join(f"{k}: {v}" for k, v in folge["stimmen"].items())
        kopf = _setze(kopf, "stimmen", "{" + paare + "}")

    # AUF-18a: Fassung der Pipeline und Tag der Erzeugung wandern mit in die
    # Bibliothek. Von hier liest der Index, von dort der Dienst, von dort die
    # App — damit an einer Folge steht, was in ihr steckt und wann sie
    # entstand. Ohne das ist eine Rueckmeldung zu ihr nicht zu deuten.
    pipeline = folge.get("pipeline") or {}
    if pipeline.get("nummer"):
        kopf = _setze(kopf, "pipeline", str(pipeline["nummer"]))
    if folge.get("erzeugt_am"):
        kopf = _setze(kopf, "erzeugt", folge["erzeugt_am"][:10])

    # Kapitelmarken ersetzen oder anhaengen (R-10: die Art steht in `art`).
    marken = folge.get("kapitelmarken") or []
    if marken:
        tabelle = ["## Kapitelmarken", "", "| Zeit | Abschnitt | Art |", "|---|---|---|"]
        tabelle += [f"| {mmss(k['sek'])} | {k['titel']} | {k['art']} |" for k in marken]
        block = "\n".join(tabelle) + "\n"
        if re.search(r"^## Kapitelmarken\s*$", rumpf, re.M):
            rumpf = re.sub(r"^## Kapitelmarken\n(?:.*?\n)??(?=^## |\Z)", block + "\n",
                           rumpf, count=1, flags=re.S | re.M)
        else:
            rumpf = rumpf.rstrip("\n") + "\n\n" + block

    lektion.write_text(f"---\n{kopf.rstrip()}\n---\n{rumpf}", encoding="utf-8")
    vorher = alt_dauer.group(1) if alt_dauer else "?"
    return (f"{lektion.name}: {mmss(int(vorher)) if vorher.isdigit() else vorher}"
            f" → {mmss(folge['dauer_sek'])}, Ton eingetragen")


def _feld(datei: Path, name: str) -> str:
    m = re.search(rf"^{name}:\s*(.+?)\s*$", datei.read_text(encoding="utf-8"), re.M)
    return (m.group(1) if m else "").strip().strip("\"'")


def _schluessel(text: str) -> str:
    """Titel vergleichbar machen.

    Anfuehrungszeichen sind am 12.09.2026 in den Folgentitel gewandert, weil
    die Warteschlange die Kopfzeile roh gelesen hat: aus `titel: "Was bewertet
    wird: ..."` wurde eine Folge, die die Zeichen im Namen traegt. Sie fallen
    hier weg, statt dass der Abgleich daran scheitert.
    """
    return " ".join(text.strip().strip("\"'").split()).casefold()


def alle() -> int:
    """Jede Lektion mit ihrer Folge verbinden, ueber den Auftragstitel.

    Verbunden wird ueber `auftrag_titel` in folge.json — das ist der Titel,
    mit dem die Folge gebaut wurde, und der kam aus der Lektion. Ueber den
    Ordnernamen zu raten waere unsicher, weil er gekuerzt und gehasht ist.
    """
    nach_titel, nach_id = {}, {}
    for datei in ARBEIT.glob("*/folge.json"):
        d = json.loads(datei.read_text(encoding="utf-8"))
        if d.get("zustand") != "fertig":
            continue
        nach_titel[_schluessel(d.get("auftrag_titel") or "")] = datei.parent
        nach_id[d.get("id")] = datei.parent

    fehlt = []
    for lektion in sorted(WISSEN.glob("eingang/*/lektionen/*.md")):
        # Zuerst ueber `auftrag`: Steht es in der Lektion, ist es die Zuordnung
        # selbst und nicht ein Rateschluss ueber Titel.
        ordner = nach_id.get(_feld(lektion, "auftrag")) \
            or nach_titel.get(_schluessel(_feld(lektion, "titel")))
        if ordner is None:
            fehlt.append(lektion.name)
            continue
        grund = passt(lektion, ordner)
        if grund:
            # Nicht verlinken und nicht schweigen: Eine falsch zugeordnete
            # Folge ist schlimmer als eine fehlende.
            print(f"  {lektion.name}: NICHT eingetragen — {grund}")
            fehlt.append(lektion.name)
            continue
        print(" ", trage_ein(lektion, ordner))
    if fehlt:
        # Ehrlich sagen, was offen ist, statt still zu schweigen (TB-8).
        print("  ohne Folge:", ", ".join(fehlt))
    return 0


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--alle":
        raise SystemExit(alle())
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(2)
    print(trage_ein(Path(sys.argv[1]), Path(sys.argv[2])))
