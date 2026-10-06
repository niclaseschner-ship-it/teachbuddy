"""Die Warteschlange: aus einem Lernpfad wird Wissen, dann Podcast, dann Mindmap.

Sie arbeitet die Kapitel der Bibliothek ab (``TEACHBUDDY_WISSEN``) und ruft
dafür die Abo-CLIs ``claude`` und ``codex`` auf; die Vertonung läuft über
Azure OpenAI (``TEACHBUDDY_AZURE_*`` in ``.env``). Vier Regeln:

* **AUF-10 — einzeln.** Agentenläufe brauchen Speicher; zwei nebeneinander
  sind auf kleinen Rechnern ein Problem, kein Geschwindigkeitsgewinn. Diese
  Warteschlange startet nie zwei.
* **AUF-21 — Lücken werden gemeldet, nicht gefüllt.** Wo das Material einen
  Abschnitt nicht trägt, schreibt der Modellierer das auf, statt zu erfinden.
  Die Warteschlange bricht deswegen nicht ab.
* **AUF-1a — kein Agent gibt frei.** Hier entsteht nichts Freigegebenes. Was
  über Nacht anfällt, liegt am Morgen als Git-Diff da, und das ist die
  Freigabe (BIB-18a).
* **APP-11 — Zwischendateien unter ``arbeit/``,** nicht im System-Temp.

**Reihenfolge nach Wert.** Läuft die Nacht nicht durch, soll das Fertige das
Wichtigere sein: erst das Wissen, dann die Prüfung, dann die Folgen, zuletzt
die Mindmap über das Kapitel. Lektionsbilder entstehen getrennt davon
(``pipeline/lektionsbild/``).

Aufruf::

    python -m pipeline.nachtlauf            # laeuft, ueberspringt Fertiges
    python -m pipeline.nachtlauf --plan     # zeigt nur, was anstuende
    python -m pipeline.nachtlauf --nur K-01 # nur ein Kapitel
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
import pfade  # noqa: E402  — liest auch .env

WISSEN = pfade.WISSEN
ARBEIT = pfade.ARBEIT / "pipeline"
STAND = ARBEIT / "stand.json"
LOGS = ARBEIT / "logs"
PYTHON = sys.executable

# **Das Zeitfenster.** Die Warteschlange zieht aus demselben Abo-Kontingent
# wie der Mensch, dem das Abo gehört. Gemessen: im Schnitt zehn Millionen
# Token je Agentenlauf — solange sie laeuft, bleibt fuer ihn kaum etwas.
#   TEACHBUDDY_FENSTER="21-8"   Standard
#   TEACHBUDDY_FENSTER="0-24"   jederzeit, fuer einen bewussten Tageslauf
FENSTER = os.environ.get("TEACHBUDDY_FENSTER", "21-8")

# Woran man erkennt, dass nicht die Aufgabe scheitert, sondern das Kontingent
# zu ist. In der Nacht auf den 12.09.2026 stand um 02:34 „You've hit your
# session limit · resets 5am" im Log — und die Warteschlange rannte in 60
# Sekunden durch die restlichen 31 Aufgaben und hakte jede als gescheitert ab.
GRENZE_ERKANNT = re.compile(
    r"(session limit|usage limit|rate.?limit|quota exceeded|resets? \d+ ?[ap]m)", re.I)
GRENZE_UHRZEIT = re.compile(r"resets? (?:at )?(\d{1,2})(?::(\d{2}))? ?([ap]m)?", re.I)

# **Welches Modell welche Arbeit macht.**
#
# Am 12.09.2026 nachgesehen: Alle 1809 Agentenantworten des Tages liefen auf
# Opus 5 — auch die, die Frontmatter editiert und Dateien umbenannt haben.
# Das ist der groesste Einzelposten der ganzen Kostenfrage gewesen, groesser
# als die hundert Werkzeugaufrufe je Lauf.
#
# Der Massstab fuer die Zuteilung ist **nicht** "wie wichtig ist der Schritt",
# sondern: **Laesst sich sein Ergebnis mechanisch pruefen?** Wo ja, darf ein
# kleines Modell arbeiten, denn ein Fehler faellt zwingend auf. Wo nein, haengt
# die Qualitaet am Urteil, und dort bleibt es beim grossen.
# **Die Eskalationsleiter.** Ein kleines Modell darf es versuchen, wo eine
# maschinische Probe sein Ergebnis prueft. Faellt es durch, wiederholt die
# Warteschlange mit dem naechstgroesseren — statt den Fehler zu behalten oder
# aufzugeben. Am 12.09.2026 hat Haiku bei elf von zwoelf Belegen auf die
# Fundstelle einer fremden Quelle gezeigt; die Probe hat es gefunden.
LEITER = ["haiku", "sonnet", "opus"]


def hoeher(modell: str) -> str:
    if modell in LEITER and LEITER.index(modell) + 1 < len(LEITER):
        return LEITER[LEITER.index(modell) + 1]
    return modell


MODELL = {
    # Fundstelle und Zitat sind gegen den Volltext nachrechenbar (TB-1).
    # Haiku hat am 12.09.2026 die maschinische Probe bestanden und war zehnmal
    # billiger — aber flach: 4 Quellen und 12 Belege fuer vier Lektionen, wo
    # Opus 8 Quellen und 99 Belege fand. Eine Lektion aus einer einzigen
    # Wissenseinheit hat der Podcast-Bauer zu Recht abgelehnt. Korrektheit war
    # also nicht das Problem, Tiefe schon — und dagegen hilft keine Probe.
    "recherche-kapitel": os.environ.get("TEACHBUDDY_MODELL_RECHERCHE", "sonnet"),
    # "Ist das ein Gedanke oder sind es zwei" hat keine mechanische Probe.
    # AUF-16 weist diese Rolle ohnehin dem Strukturkopf zu.
    "wissen": os.environ.get("TEACHBUDDY_MODELL_WISSEN", "opus"),
    # Die Gliederung ist ein Urteil.
    "mindmap-analyse": os.environ.get("TEACHBUDDY_MODELL_ANALYSE", "opus"),
    }

ZEIT_RECHERCHE = 3600
ZEIT_MODELL = 2700
ZEIT_SKRIPT = 2400
ZEIT_GRAFIK = 2400

# Unter so viel freiem Arbeitsspeicher wird nicht gestartet, sondern gewartet.
MIN_FREI_MB = int(os.environ.get("TEACHBUDDY_MIN_FREI_MB", "900"))


def nimm_das_schloss():
    """Genau ein Lauf zur Zeit (AUF-10).

    Zwei Warteschlangen nebeneinander heisst zwei Agentenlaeufe nebeneinander,
    und das ist auf kleinen Rechnern ein Speicherproblem. Das Schloss haengt am Prozess:
    Stirbt er, faellt es von selbst, und die systemd-Unit kann uebernehmen.
    Eine Datei mit einer PID darin wuerde nach einem Absturz liegen bleiben
    und den Neustart blockieren — genau dann, wenn er gebraucht wird.
    """
    ARBEIT.mkdir(parents=True, exist_ok=True)
    schloss = open(ARBEIT / "lauf.lock", "w")
    try:
        fcntl.flock(schloss, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return None
    schloss.write(str(os.getpid()))
    schloss.flush()
    return schloss


def wann_wieder(text: str) -> datetime | None:
    """Aus „resets 5am" den naechsten Zeitpunkt machen, zu dem es weitergeht."""
    m = GRENZE_UHRZEIT.search(text)
    if not m:
        return None
    stunde = int(m.group(1)) % 12
    if (m.group(3) or "").lower() == "pm":
        stunde += 12
    minute = int(m.group(2) or 0)
    jetzt_ = datetime.now().astimezone()
    ziel = jetzt_.replace(hour=stunde, minute=minute, second=0, microsecond=0)
    if ziel <= jetzt_:
        ziel += timedelta(days=1)
    return ziel


def lade_zugaenge() -> list[str]:
    """Zugangsdaten in die eigene Umgebung holen. Gibt zurueck, was fehlt.

    Ohne Azure-Schluessel gibt es keine Vertonung (POD-7a). Das soll beim
    Start auffallen, nicht in der Nacht.
    """
    noetig = ("TEACHBUDDY_AZURE_OPENAI_ENDPOINT", "TEACHBUDDY_AZURE_OPENAI_KEY",
              "TEACHBUDDY_AZURE_OPENAI_DEPLOYMENT")
    return [n for n in noetig if not os.environ.get(n)]


def jetzt() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def im_fenster() -> bool:
    von, bis = (int(x) for x in FENSTER.split("-"))
    st = datetime.now().astimezone().hour
    return von <= st < bis if von < bis else (st >= von or st < bis)


def warte_aufs_fenster(schreib) -> None:
    gesagt = False
    while not im_fenster():
        if not gesagt:
            von = FENSTER.split("-")[0]
            schreib(f"  ausserhalb des Arbeitsfensters ({FENSTER} Uhr), wartet bis {von}:00")
            gesagt = True
        time.sleep(300)


def frei_mb() -> int:
    """Freier Arbeitsspeicher in MB; ohne /proc (macOS, Windows) unbekannt = genug."""
    try:
        for zeile in Path("/proc/meminfo").read_text().splitlines():
            if zeile.startswith("MemAvailable:"):
                return int(zeile.split()[1]) // 1024
    except OSError:
        pass
    return 10_000


def warte_auf_speicher(schreib) -> None:
    gewartet = 0
    while frei_mb() < MIN_FREI_MB:
        if gewartet == 0:
            schreib(f"  wartet auf Speicher ({frei_mb()} MB frei, {MIN_FREI_MB} noetig)")
        time.sleep(60)
        gewartet += 60
        if gewartet > 1800:
            schreib("  Speicher bleibt knapp — es wird trotzdem weitergemacht")
            return


# --------------------------------------------------------------------------
# Stand
# --------------------------------------------------------------------------

def lies_stand() -> dict:
    if STAND.is_file():
        return json.loads(STAND.read_text(encoding="utf-8"))
    return {"erledigt": {}, "begonnen": jetzt()}


def schreib_stand(stand: dict) -> None:
    STAND.write_text(json.dumps(stand, indent=2, ensure_ascii=False), encoding="utf-8")


# --------------------------------------------------------------------------
# Was es zu tun gibt
# --------------------------------------------------------------------------

def naechste_nummer(praefix: str) -> str:
    """Die naechste freie Nummer im Eingang, damit nichts ueberschrieben wird."""
    vorhanden = [d.name for d in (WISSEN / "eingang").glob(f"{praefix}-*") if d.is_dir()]
    hoechste = 0
    for name in vorhanden:
        m = re.match(rf"{praefix}-(\d+)$", name)
        if m:
            hoechste = max(hoechste, int(m.group(1)))
    return f"{praefix}-{hoechste + 1:03d}"


def zahl_einheiten(abschnitt: str) -> int:
    """Wie viele Wissenseinheiten die Lektion dieses Abschnitts nennt.

    0 heisst: Es gibt noch keine Lektion. Das ist etwas anderes als eine
    Lektion, die zu wenige traegt.
    """
    datei = lektion_datei(abschnitt)
    if datei is None:
        return 0
    m = re.search(r"^wissenseinheiten:\s*\[(.*?)\]\s*$",
                  datei.read_text(encoding="utf-8", errors="replace"), re.M)
    return len([x for x in (m.group(1) if m else "").split(",") if x.strip()])


def lektion_da(abschnitt: str) -> bool:
    for datei in WISSEN.glob("eingang/*/lektionen/*.md"):
        text = datei.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"^abschnitt:\s*{abschnitt}\s*$", text, re.M):
            return True
    return False


def lektion_datei(abschnitt: str) -> Path | None:
    for datei in sorted(WISSEN.glob("eingang/*/lektionen/*.md")):
        text = datei.read_text(encoding="utf-8", errors="replace")
        if re.search(rf"^abschnitt:\s*{abschnitt}\s*$", text, re.M):
            return datei
    return None


def kopffeld(datei: Path, feld: str) -> str | None:
    """Ein Kopffeld lesen, ohne seine YAML-Anfuehrungszeichen mitzunehmen.

    Ohne das Abstreifen wanderten sie in den Titel der Folge: aus
    `titel: "Was bewertet wird: ..."` wurde eine Folge, die die Zeichen im
    Namen trug, und der Abgleich Folge-zu-Lektion fiel darauf herein.
    """
    m = re.search(rf"^{feld}:\s*(.+?)\s*$", datei.read_text(encoding="utf-8"), re.M)
    return m.group(1).strip().strip("\"'") if m else None


def kapitel_aus_der_bibliothek() -> list[dict]:
    """Die Kapitel, wie sie in der Bibliothek stehen — nicht fest verdrahtet.

    Bis zum 12.09.2026 standen die dreizehn Abschnitte von P-01 als Konstante
    im Skript. Mit einem zweiten Lernpfad ginge das nicht mehr, und eine
    zweite Wahrheit ueber die Gliederung waere ohnehin falsch (BIB-18).
    """
    raus = []
    for datei in sorted((WISSEN / "kapitel").glob("K-*.md")):
        text = datei.read_text(encoding="utf-8")
        feld = lambda n, v="": (re.search(rf"^{n}:\s*(.+?)\s*$", text, re.M) or [None, v])[1]
        lekt = re.search(r"^lektionen:\s*\[(.*?)\]\s*$", text, re.M)
        raus.append({
            "id": feld("id", datei.stem),
            "pfad": feld("pfad"),
            "welle": int(feld("welle", "0") or 0),
            "nummer": int(feld("nummer", "1") or 1),
            "stufe": feld("tiefenstufe", "Überblick"),
            "lektionen": [x.strip() for x in (lekt.group(1) if lekt else "").split(",") if x.strip()],
        })
    raus.sort(key=lambda k: (k["welle"], k["nummer"]))
    return raus


def _genanntes_material(kapitel_id: str) -> list[str]:
    """Das Feld `material:` der Kapiteldatei — die ausdrueckliche Zuordnung."""
    datei = WISSEN / "kapitel" / f"{kapitel_id}.md"
    if not datei.is_file():
        return []
    m = re.search(r"^material:\s*\[(.*?)\]\s*$", datei.read_text(encoding="utf-8"), re.M)
    return [x.strip() for x in m.group(1).split(",") if x.strip()] if m else []


def material_ordner(kapitel_id: str) -> list[str]:
    """Welche Eingangsordner diesem Kapitel gelten.

    Zuerst das Feld `material:` der Kapiteldatei: Das ist die Zuordnung selbst.
    P-01 braucht es, weil A-002 bis A-005 fuer einzelne Abschnitte gelaufen
    sind, bevor es Kapitel gab. Danach die Auftraege, die das Kapitel selbst
    nennen — so tragen sich neue Rechercheläufe von allein ein.
    """
    ordner = [n for n in _genanntes_material(kapitel_id)
              if (WISSEN / "eingang" / n).is_dir()]
    for auftrag in sorted((WISSEN / "eingang").glob("A-*/AUFTRAG.md")):
        name = auftrag.parent.name
        if name not in ordner and kapitel_id in auftrag.read_text(
                encoding="utf-8", errors="replace")[:2000]:
            ordner.append(name)
    return ordner


def hat_material(kapitel_id: str) -> bool:
    return bool(material_ordner(kapitel_id))


def aufgaben() -> list[dict]:
    """Die ganze Arbeit als Liste, Welle fuer Welle.

    **Ein Kapitel wird fertig, bevor das naechste beginnt.** Frueher lief erst
    alles Wissen, dann alle Folgen, dann alle Abbildungen. Bei einem Lernpfad
    war das richtig; bei Wellen ist es falsch, denn dann ist nach dem Abbruch
    kein einziges Kapitel benutzbar, sondern alle halb.
    """
    raus: list[dict] = []
    for k in kapitel_aus_der_bibliothek():
        kid = k["id"]

        # **Recherche, wenn kein Material da ist — oder wenn es zu duenn ist.**
        # "Kein Material" allein reicht als Bedingung nicht: Nach einem
        # Lueckenbericht (AUF-21) braucht das Kapitel einen zweiten Lauf,
        # obwohl schon etwas daliegt. Am 12.09.2026 hat die Warteschlange
        # deshalb eine beschlossene Nachrecherche stillschweigend uebersprungen.
        #
        # Der Massstab ist mechanisch: **Eine Lektion aus weniger als zwei
        # Wissenseinheiten ist keine Lektion** — genau das hat der
        # Podcast-Bauer bei L-M3 selbst festgestellt und die Vertonung
        # verweigert.
        duenn = [a for a in k["lektionen"] if 0 < zahl_einheiten(a) < 2]
        if not hat_material(kid) or duenn:
            raus.append({"id": f"recherche-{kid}", "art": "recherche-kapitel",
                         "kapitel": kid, "abschnitt": None,
                         "grund": ("zu duenn: " + ", ".join(duenn)) if duenn
                                  else "kein Material"})
        # **Ein Modellierlauf je Kapitel, nicht je Lektion.** Sonst wandert
        # dasselbe Material achtmal in einen Kontext.
        # **Auch zu duenne Lektionen sind offen.** Nach einer Nachrecherche
        # liegt neues Material da, aber die Lektion existiert schon — und die
        # Warteschlange sah keinen Grund, sie noch einmal zu bauen. Am
        # 12.09.2026 lief so eine Sonnet-Recherche ins Leere: 20 Belege
        # geholt, keiner verwendet, L-M3 blieb bei einer Einheit.
        offen_lekt = [a for a in k["lektionen"]
                      if not lektion_da(a) or zahl_einheiten(a) < 2]
        if offen_lekt:
            raus.append({"id": f"wissen-{kid}", "art": "wissen",
                         "kapitel": kid, "abschnitt": None})
        # **Die Gegenprobe** (AUF-15/16). Sie stand seit dem ersten Tag in der
        # Spec und ist beim Bau der Warteschlange schlicht liegen geblieben:
        # Claude recherchiert, modelliert, analysiert — und prueft sich selbst.
        # Ein Modell, das seinen eigenen Text prueft, findet den Fehler genau
        # dort nicht, wo er entstanden ist.
        #
        # Sie laeuft auf **GPT** und blockiert nichts: Beanstandungen sind
        # Befunde, ueber die der Mensch entscheidet (BIB-16, AUF-1a).
        # Grosse Kapitel werden in Scheiben geprueft. Ein Kapitel kann fast
        # eine Million Zeichen Material tragen; das passt in keinen Lauf. Stillschweigend nur
        # einen Teil zu pruefen und "geprueft" zu melden waere schlimmer als
        # gar nicht zu pruefen — also wird geteilt und jede Scheibe gezaehlt.
        for nr in range(1, pruefscheiben(kid) + 1):
            raus.append({"id": f"pruefung-{kid}-{nr}", "art": "pruefung",
                         "kapitel": kid, "abschnitt": str(nr)})
        for a in k["lektionen"]:
            raus.append({"id": f"podcast-{a}", "art": "podcast", "kapitel": kid, "abschnitt": a})
        # Das Bild einer Lektion entsteht ausserhalb dieser Warteschlange,
        # gemalt ueber das ChatGPT-Abo (E-19d, pipeline/lektionsbild/).
        #
        # Die Mindmap des Kapitels ist eine Gliederung (E-19a); die App
        # zeichnet sie selbst als aufklappbaren Knotenbaum.
        raus.append({"id": f"mindmap-analyse-{kid}",
                     "art": "mindmap-analyse", "kapitel": kid, "abschnitt": None})
    return [a for a in raus if not schon_in_der_bibliothek(a)]


def schon_in_der_bibliothek(auf: dict) -> bool:
    """Liegt das Ergebnis schon in der Bibliothek? Dann gibt es nichts zu tun.

    Der Lauf-Stand (``stand.json``) kennt nur, was **diese** Werkstatt gebaut
    hat. Eine Bibliothek, die aus einem anderen Klon kommt, waere sonst
    komplett offen — und die Warteschlange wuerde jede Folge neu vertonen und
    dafuer bezahlen. Massgeblich ist deshalb, was in den Dateien steht.
    """
    kid = auf.get("kapitel") or ""
    if auf["art"] == "pruefung":
        return (WISSEN / "pruefung" / f"{kid}-{auf['abschnitt']}.md").is_file()
    if auf["art"] == "mindmap-analyse":
        return (WISSEN / "mindmap" / f"{kid}.md").is_file()
    if auf["art"] == "podcast":
        datei = lektion_datei(auf["abschnitt"])
        if datei is None or not kopffeld(datei, "audio"):
            return False
        ordner = pfade.PODCAST_ARBEIT / (kopffeld(datei, "auftrag") or "")
        if not ordner.is_dir():
            return True          # anderswo gebaut; der Kopf der Lektion zaehlt
        from podcast.eintragen import passt
        return passt(datei, ordner) is None
    return False


# --------------------------------------------------------------------------
# Ausfuehren
# --------------------------------------------------------------------------

def claude(prompt: str, *, cwd: Path, log: Path, zeit: int, modell: str = "opus") -> int:
    log.parent.mkdir(parents=True, exist_ok=True)
    befehl = ["claude", "-p", prompt, "--model", modell,
              "--permission-mode", "acceptEdits",
              "--allowedTools", "Read", "Write", "Edit", "Glob", "Grep", "Bash"]
    with log.open("w", encoding="utf-8") as f:
        f.write(f"[Modell: {modell}]\n")
        f.flush()
        return subprocess.run(befehl, cwd=str(cwd), stdout=f,
                              stderr=subprocess.STDOUT, timeout=zeit).returncode


BUENDEL = """
**Schreib genau eine Datei: `{buendel}`.** Sie enthaelt alles, was entstehen
soll, mit dieser Marke davor::

    <<<DATEI unterordner/name.md>>>
    ---
    id: …
    ---
    Text …
    <<<DATEI unterordner/naechster.md>>>
    …

Ein Skript zerlegt sie danach und legt die Dateien an. **Lege keine einzelnen
Dateien an und editiere nichts nach.** Am 12.09.2026 gemessen: 138 von 150
Werkzeugaufrufen eines Laufs waren Dateien hin- und herschieben, und weil
jeder Aufruf den ganzen Kontext erneut liest, kostet genau das fast alles.

Um Anfuehrungszeichen im Kopf musst du dich nicht kuemmern; das Skript setzt
sie, wo ein Wert einen Doppelpunkt enthaelt.
"""


SPARSAM_RECHERCHE = """
**Arbeite sparsam, aber lies die Quellen.** Jeder Werkzeugaufruf liest deinen
ganzen bisherigen Kontext erneut mit; hundert Aufrufe kosten zehn Millionen
Token. Sparen darfst du an Aufrufen, **nicht am Lesen der Quelle**: Ein
Rechercheur, der nicht liest, kann nur erfinden.

- **Lies jede Datei genau einmal**, und hol den Volltext in einem Zug statt in
  Haeppchen.
- **Kein Stoebern** ausserhalb dessen, was der Auftrag nennt.
- **Schreib das Buendel in einem Schritt**, nicht in vielen kleinen.
"""


SPARSAM = """
**Arbeite sparsam.** Jeder Werkzeugaufruf liest deinen ganzen bisherigen
Kontext erneut mit. Am 12.09.2026 gemessen: hundert Aufrufe je Lauf, zehn
Millionen Token. Das Kontingent, das du verbrauchst, ist dasselbe, aus dem
der Mensch arbeitet.

Daraus folgt:
- **Lies jede Datei genau einmal.** Was du gelesen hast, steht in deinem
  Kontext; es noch einmal zu lesen kostet doppelt und bringt nichts.
- **Lies keine Quellen-Volltexte.** Die Belege tragen Aussage und Fundstelle;
  dafuer sind sie da. Volltexte sind Megabytes.
- **Kein Stoebern.** Oeffne, was der Auftrag nennt, und nicht, was daneben
  liegt.
- **Schreib in wenigen grossen Schritten**, nicht in vielen kleinen.
"""


def _entfalte(buendel: Path, wurzel: Path, log: Path) -> int:
    """Das Buendel in Dateien zerlegen. Fehlt es, ist der Lauf gescheitert."""
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))      # als Datei gestartet, nicht als Modul
    from pipeline.entfalten import entfalten
    if not buendel.is_file():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\nKEIN BUENDEL unter {buendel} — nichts zu entfalten.\n")
        return 91
    n, notizen = entfalten(buendel, wurzel)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n--- entfaltet: {n} Dateien ---\n")
        for x in notizen:
            f.write(f"  berichtigt: {x}\n")
    buendel.unlink()          # Wegwerfware, die Dateien sind die Wahrheit
    return 0


def sichere(aufgabe: str, schreib) -> None:
    """Nach jedem gelungenen Schritt in der Bibliothek committen.

    Am 12.09.2026 habe ich einen erfolgreichen Rechercheertrag beim Aufraeumen
    geloescht, weil ich ihn fuer einen verworfenen hielt. Er war nie
    committet und damit weg. Ein Commit je Schritt macht jede Handbewegung
    rueckholbar — und BIB-18a will den Git-Diff ohnehin, er ist die Freigabe.
    """
    import subprocess as sp
    try:
        stand = sp.run(["git", "status", "--porcelain", "--", "."], cwd=str(WISSEN),
                       capture_output=True, text=True, timeout=60).stdout.strip()
        if not stand:
            return
        sp.run(["git", "add", "-A", "--", "."], cwd=str(WISSEN), timeout=120, check=True)
        sp.run(["git", "-c", "user.name=Warteschlange",
                "-c", "user.email=noreply@anthropic.com",
                "commit", "-q", "-m", f"{aufgabe}: Ertrag gesichert",
                "-m", "Automatisch nach einem gelungenen Schritt. Freigegeben ist "
                      "damit nichts (AUF-1a) — der Diff ist die Freigabe (BIB-18a).",
                "--", "."],
               cwd=str(WISSEN), timeout=120, check=True)
        schreib(f"  gesichert: {len(stand.splitlines())} Dateien")
    except Exception as f:                                   # noqa: BLE001
        schreib(f"  NICHT gesichert ({type(f).__name__}) — bitte von Hand ansehen")


def naechste_quellennummer() -> int:
    """Die naechste freie Q-Nummer.

    Ohne sie faengt ein Agent bei Q-0001 an und ueberschreibt bestehende
    Quellen — am 12.09.2026 genau so passiert. Fundstellen und Belege tragen
    die Quellennummer in sich (F-0011-01, B-0011-01), also haengt alles daran.
    """
    hoechste = 0
    for datei in WISSEN.glob("eingang/*/quellen/Q-*"):
        m = re.search(r"Q-(\d+)", datei.name)
        if m:
            hoechste = max(hoechste, int(m.group(1)))
    return hoechste + 1


def naechste_we_nummer() -> int:
    """Die naechste freie WE-Nummer — ausgerechnet, nicht vom Agenten gesucht.

    Er brauchte dafuer ein Glob ueber alle Einheiten und einen Read; das sind
    zwei Aufrufe mit vollem Kontext fuer eine Zahl.
    """
    hoechste = 0
    for datei in WISSEN.glob("eingang/*/einheiten/WE-*.md"):
        m = re.search(r"WE-(\d+)", datei.name)
        if m:
            hoechste = max(hoechste, int(m.group(1)))
    return hoechste + 1


def tu_recherche(a: str, log: Path, kapitel: str | None = None,
                 modell: str | None = None) -> int:
    """Recherche fuer ein ganzes Kapitel, nicht fuer eine Lektion.

    Ein Auftrag ueber acht verwandte Abschnitte kostet kaum mehr als ueber
    einen und liefert Nebenertrag fuer alle. So hat A-003 funktioniert.
    """
    nr = naechste_nummer("A")
    kid = kapitel or "?"
    modell = modell or MODELL["recherche-kapitel"]
    q0 = naechste_quellennummer()
    prompt = f"""Du fuehrst den Auftrag {REPO}/auftraege/rechercheur.md aus.

**Die Quellen beginnen bei Q-{q0:04d}** und zaehlen fortlaufend weiter. Such
nicht nach freien Nummern, die Zahl ist ausgerechnet. Fundstellen und Belege
tragen die Nummer ihrer Quelle: zu Q-{q0:04d} gehoeren F-{q0:04d}-01,
F-{q0:04d}-02 und B-{q0:04d}-01, B-{q0:04d}-02 und so fort.

**Ein Beleg nennt die Fundstelle, aus der er folgt, und keine andere.** Das
wird nach dem Lauf maschinell geprueft: Jede `fundstelle:` muss es geben, und
sie muss zur selben Quelle gehoeren.
{_vorhandenes(kid)}

Arbeitsverzeichnis: {WISSEN}
Gegenstand: **Kapitel {kid}**, alle seine Lektionen auf einmal. Was es
umfasst, steht in kapitel/{kid}.md; die Gliederung der einzelnen Abschnitte
in pfade/ (der Lernpfad, den kapitel/{kid}.md unter `pfad` nennt).

Lege deinen Lauf unter eingang/{nr}/ an. **Die erste Zeile von
eingang/{nr}/AUFTRAG.md nennt `{kid}`** — daran erkennt die Warteschlange,
dass dieses Kapitel Material hat.

Erwartet werden AUFTRAG.md, quellen/, belege/, bericht.md,
gliederungsbefund.md (BIB-28) und **zuordnung.md** — alle als Bündel.

`zuordnung.md` ist eine Tabelle „Abschnitt | Beleg-IDs" ueber alle Abschnitte
des Kapitels. Sie ist kein Beiwerk: Ohne sie muss jeder spaetere
Modellierlauf saemtliche Belege des Kapitels lesen, um die wenigen zu finden,
die ihn angehen. Bei acht Lektionen ist das achtmal dieselbe Last. Ein Beleg
darf bei mehreren Abschnitten stehen; einer, der zu keinem gehoert, gehoert in
eine Zeile „ohne Abschnitt" mit Begruendung.

**Nichts ohne Fundstelle** (TB-1). Findest du zu einem Abschnitt nichts,
schreib das in den Bericht, statt es zu fuellen (AUF-21).

{BUENDEL.format(buendel=f"eingang/{nr}/buendel.md")}
{SPARSAM_RECHERCHE}
Sprache: Deutsch."""
    code = claude(prompt, cwd=WISSEN, log=log, zeit=ZEIT_RECHERCHE, modell=modell)
    if code:
        return code
    ordner = WISSEN / "eingang" / nr
    code = _entfalte(ordner / "buendel.md", ordner, log)
    if code:
        return code

    # **Die Probe entscheidet, nicht der Eindruck.** Besteht der Ertrag sie
    # nicht, wandert er nicht in die Bibliothek, sondern wird verworfen und
    # der Lauf gilt als gescheitert — dann greift die Eskalationsleiter.
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from pipeline.belegprobe import pruefe
    klagen = pruefe(ordner)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"\n--- Belegprobe: {len(klagen)} Befunde ---\n")
        for k in klagen[:40]:
            f.write(f"  {k}\n")
    if klagen:
        import shutil
        shutil.rmtree(ordner, ignore_errors=True)
        return 92
    return 0


def _vorhandenes(kapitel: str) -> str:
    """Was zu diesem Kapitel schon erhoben ist — damit ergaenzt statt
    wiederholt wird.

    Nach einem Lueckenbericht (AUF-21) wird nachrecherchiert. Ohne diesen
    Hinweis holt der zweite Lauf dieselben Quellen noch einmal und die Luecke
    bleibt.
    """
    ordner = material_ordner(kapitel)
    if not ordner:
        return ""
    zeilen = [
        "",
        "**Zu diesem Kapitel ist schon erhoben worden**, und zwar in:",
    ]
    for name in ordner:
        belege = len(list((WISSEN / "eingang" / name / "belege").glob("*.md")))
        zeilen.append(f"  - eingang/{name}/ ({belege} Belege)")
    zeilen += [
        "",
        "**Lies deren `luecken.md` und `bericht.md` zuerst.** Dein Auftrag ist",
        "zu **ergaenzen**, nicht zu wiederholen: Was dort schon belegt ist,",
        "belegst du nicht noch einmal. Geh gezielt auf das, was als fehlend",
        "gemeldet ist, und auf die Abschnitte, die zu duenn geblieben sind.",
    ]
    return "\n".join(zeilen)


def _material_von(kapitel: str) -> str:
    """Die Eingangsordner, die diesem Kapitel gelten — und nur die.

    **Der groesste Sparhebel.** Bis zum 12.09.2026 stand im Auftrag "alle
    Belege unter A-002 und A-003", und der Agent zog 372 Belegdateien in
    seinen Kontext, die er dann durch hundert Aufrufe mitschleppte.
    """
    ordner = [f"eingang/{n}/belege/" for n in material_ordner(kapitel)]
    return "\n".join(f"- {o}" for o in ordner) or "- (kein zugeordnetes Material)"


def tu_wissen(a: str | None, log: Path, kapitel: str | None = None) -> int:
    """Alle noch fehlenden Lektionen eines Kapitels in **einem** Lauf.

    Vorher lief ein Auftrag je Lektion, und jeder zog dasselbe Material in
    seinen Kontext. Bei acht Lektionen war das achtmal dieselbe Last.
    """
    nr = naechste_nummer("M")
    kid = kapitel
    kap = next((k for k in kapitel_aus_der_bibliothek() if k["id"] == kid), None)
    offen = [x for x in (kap["lektionen"] if kap else [])
             if not lektion_da(x) or zahl_einheiten(x) < 2]
    if not offen:
        return 0
    we = naechste_we_nummer()
    liste = "\n".join(
        f"  - {x}: Lektion L-{x}, nummer {kap['lektionen'].index(x) + 1}"
        + (f"  ← existiert schon, ist aber mit {zahl_einheiten(x)} Einheit(en) zu "
           "duenn und wird **neu gebaut**" if lektion_da(x) else "")
        for x in offen)

    prompt = f"""Du fuehrst den Auftrag {REPO}/auftraege/modellierer.md aus.

Arbeitsverzeichnis: {WISSEN}
Gegenstand: **Kapitel {kid}**, und zwar diese Abschnitte auf einmal:
{liste}

Ihre Gliederung steht im Lernpfad, den kapitel/{kid}.md unter `pfad` nennt.
Lies dort **nur diese Abschnitte**, nicht den ganzen Pfad.

Material — genau diese Ordner, keine anderen:
{_material_von(kid)}

**Lies zuerst zuordnung.md** im selben Auftragsordner, falls vorhanden. Dort
steht, welche Belege zu welchem Abschnitt gehoeren; lies nur diese. Fehlt die
Datei, arbeite den Belegordner einmal durch — einmal fuer alle Abschnitte,
nicht je Abschnitt neu.

Lies dazu bericht.md desselben Auftrags: dort steht, wo die Quellenlage duenn
ist und wo Quellen einander widersprechen.

**Die Wissenseinheiten beginnen bei WE-{we:04d}** und zaehlen fortlaufend
weiter. Such nicht nach freien Nummern, die Zahl ist ausgerechnet.

Je Einheit gehoeren in den Kopf: `id`, `titel` (die Behauptung, ein Satz),
`stichwort` (zwei bis vier Woerter, der Gegenstand statt der Behauptung,
MMP-3), `grad`, `belegt_durch`, `setzt_voraus`, `siehe_auch`, `gilt_ab`.
Je Lektion: `id`, `kapitel: {kid}`, `abschnitt`, `nummer`, `titel`,
`dauer_sek`, `wissenseinheiten`.

Ins Buendel gehoeren:
- AUFTRAG.md
- einheiten/WE-*.md
- lektionen/L-*.md fuer jeden genannten Abschnitt
- schnittbericht.md
- luecken.md — **Pflicht** (AUF-21), je Abschnitt ein eigener Absatz. Was der
  Abschnitt braucht und das Material nicht hergibt. Gibt es nichts, steht das
  da.

**Erfinde nichts.** Ein duenner belegter Abschnitt ist besser als ein voller
erfundener (TB-1).

{BUENDEL.format(buendel=f"eingang/{nr}/buendel.md")}
{SPARSAM}
Sprache: Deutsch. Keine Gedankenstriche als Gliederungszeichen."""
    code = claude(prompt, cwd=WISSEN, log=log, zeit=ZEIT_MODELL,
                   modell=MODELL["wissen"])
    return code or _entfalte(WISSEN / "eingang" / nr / "buendel.md", WISSEN / "eingang" / nr, log)


def _kurzname(titel: str) -> str:
    """Der Anfang des Ordnernamens, den podcast.bauen aus dem Titel bildet."""
    rein = re.sub(r"[^a-z0-9]+", "-", titel.lower().replace("ä", "ae")
                  .replace("ö", "oe").replace("ü", "ue").replace("ß", "ss"))
    return rein.strip("-")[:24]


PRUEF_ZEICHEN = 110_000       # was ein Codex-Lauf verlaesslich traegt


def _kapitel_einheiten(kapitel_id: str) -> list[str]:
    import sqlite3
    db = sqlite3.connect(pfade.INDEX)
    db.row_factory = sqlite3.Row
    we = [r["einheit_id"] for r in db.execute(
        "SELECT DISTINCT le.einheit_id FROM lektion_einheiten le"
        " JOIN lektionen l ON l.id = le.lektion_id WHERE l.kapitel = ?"
        " ORDER BY le.einheit_id", (kapitel_id,))]
    db.close()
    return we


def pruefscheiben(kapitel_id: str) -> int:
    """In wie viele Scheiben das Material eines Kapitels zerfaellt."""
    ganz = len(_pruefmaterial(kapitel_id))
    return max(1, -(-ganz // PRUEF_ZEICHEN))


def tu_pruefung(a: str | None, log: Path, kapitel: str | None = None) -> int:
    """Die Gegenprobe durch das andere Modell (AUF-15, AUF-16).

    **Sie blockiert nicht.** Ein Befund ist ein Befund, keine Sperre — ueber
    Nachbesserung entscheidet der Mensch (AUF-22). Der Lauf gilt als gelungen,
    wenn ein Bericht entstanden ist, auch wenn er voller Beanstandungen steht.
    Ein Pruefer, der den Betrieb anhaelt, wird abgeschaltet; einer, der
    schreibt, wird gelesen.
    """
    import shutil
    import sys
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    from podcast.skript import finde_codex

    kid = kapitel
    scheibe = int(a or 1)
    von_wie_vielen = pruefscheiben(kid)
    arbeit = ARBEIT / "pruefung" / f"{kid}-{scheibe}"
    arbeit.mkdir(parents=True, exist_ok=True)
    (arbeit / "tmp").mkdir(exist_ok=True)          # APP-11: nicht nach /tmp
    shutil.copyfile(REPO / "auftraege" / "pruefer.md", arbeit / "auftrag.md")

    # Das Material: die Einheiten des Kapitels mit ihren Belegen und
    # Fundstellen, ausgeschrieben. Der Pruefer soll nicht suchen muessen.
    (arbeit / "material.md").write_text(
        _pruefmaterial(kid, scheibe, von_wie_vielen), encoding="utf-8")
    ziel = arbeit / "befunde.md"
    if ziel.exists():
        ziel.unlink()

    prompt = (
        "Lies `auftrag.md` und `material.md` in diesem Verzeichnis und fuehre "
        f"den Auftrag aus. Gegenstand: Kapitel {kid}, Teil {scheibe} von "
        f"{von_wie_vielen}. Schreibe das Ergebnis "
        "nach `befunde.md` in diesem Verzeichnis. Lege nichts anderes an. "
        "Sprache: Deutsch.")
    umgebung = dict(os.environ, TMPDIR=str(arbeit / "tmp"))
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        f.write("[Modell: GPT über codex exec — die Gegenprobe, AUF-16]\n")
        f.flush()
        try:
            subprocess.run([finde_codex(), "exec", "--sandbox", "workspace-write",
                            "--skip-git-repo-check", prompt],
                           cwd=str(arbeit), stdout=f, stderr=subprocess.STDOUT,
                           env=umgebung, timeout=ZEIT_MODELL)
        except Exception as fehler:                       # noqa: BLE001
            f.write(f"\nPruefer nicht erreichbar: {type(fehler).__name__}: {fehler}\n")
            return 95
    if not ziel.is_file():
        with log.open("a", encoding="utf-8") as f:
            f.write("\nKEIN ERTRAG: befunde.md wurde nicht geschrieben.\n")
        return 93
    # Der Bericht gehoert in die Bibliothek, nicht in den Arbeitsordner.
    (WISSEN / "pruefung").mkdir(exist_ok=True)
    shutil.copyfile(ziel, WISSEN / "pruefung" / f"{kid}-{scheibe}.md")
    return 0


def _pruefmaterial(kapitel_id: str, scheibe: int = 0, von: int = 1) -> str:
    """Einheiten des Kapitels mit ihren Belegen und Fundstellen, ausgeschrieben.

    ``scheibe`` 0 heisst: alles (fuer die Groessenmessung). Sonst der Anteil,
    der zu dieser Scheibe gehoert.
    """
    import sqlite3
    db = sqlite3.connect(pfade.INDEX)
    db.row_factory = sqlite3.Row
    we = _kapitel_einheiten(kapitel_id)
    if not we:
        return f"# {kapitel_id}\n\nKeine Wissenseinheiten.\n"
    alle = len(we)
    if scheibe:
        breite = -(-alle // von)
        we = we[(scheibe - 1) * breite: scheibe * breite]
    teile = [f"# Material zu {kapitel_id}", ""]
    if scheibe and von > 1:
        teile += [f"**Teil {scheibe} von {von}.** Dieses Kapitel hat {alle} "
                  f"Wissenseinheiten; hier stehen {len(we)} davon. Was nicht "
                  "hier steht, ist nicht geprueft — schreib das in den "
                  "Abschnitt NICHT GEPRUEFT.", ""]
    teile += [f"{len(we)} Wissenseinheiten mit ihren Belegen und Fundstellen.", ""]
    for wid in we:
        z = db.execute("SELECT * FROM einheiten WHERE id = ?", (wid,)).fetchone()
        if z is None:
            continue
        teile += [f"\n## {wid} — {z['titel']}", ""]
        if z["kurzfassung"]:
            teile.append(f"*Kurzfassung:* {z['kurzfassung'].strip()}")
        if z["inhalt"]:
            teile += ["", z["inhalt"].strip()]
        for b in db.execute(
                "SELECT b.*, f.zitat, f.stelle, f.quelle_id FROM belege b"
                "  LEFT JOIN fundstellen f ON f.id = b.fundstelle_id"
                " WHERE b.id IN (SELECT von FROM kanten"
                "                 WHERE nach = ? AND typ = 'stuetzt')", (wid,)):
            teile.append(f"\n### Beleg {b['id']} → {b['fundstelle_id']}"
                         f" (Zuversicht {b['zuversicht']})")
            if b["aussage"]:
                teile.append(f"*Aussage:* {b['aussage'].strip()}")
            if b["begruendung"]:
                teile.append(f"*Begruendung:* {b['begruendung'].strip()}")
            if b["zitat"]:
                teile.append(f"*Wortlaut ({b['quelle_id']}, {b['stelle']}):* "
                             f"„{b['zitat'].strip()}“")
    db.close()
    return "\n".join(teile)


def tu_podcast(a: str, log: Path, kapitel: str | None = None) -> int:
    datei = lektion_datei(a)
    if datei is None:
        return 90                       # keine Lektion: nichts zu vertonen
    # „Hat schon Audio" genuegt nicht: Es koennte die Folge einer frueheren
    # Fassung sein. Geprueft wird, ob sie aus denselben Einheiten gebaut ist.
    if kopffeld(datei, "audio"):
        import sys
        if str(REPO) not in sys.path:
            sys.path.insert(0, str(REPO))
        from podcast.eintragen import passt
        auftrag = kopffeld(datei, "auftrag")
        ordner = pfade.PODCAST_ARBEIT / (auftrag or "")
        if auftrag and ordner.is_dir() and passt(datei, ordner) is None:
            return 0                    # schon vertont, und es passt
    einheiten = datei.parent.parent / "einheiten"
    nur = (kopffeld(datei, "wissenseinheiten") or "").strip("[] ")
    titel = kopffeld(datei, "titel") or f"Abschnitt {a}"
    # **Ein zwischengespeichertes Urteil gilt nur fuer sein Material.** Am
    # 12.09.2026 lehnte der Bauer L-M3 ab ("nur eine Wissenseinheit"), danach
    # wurde die Lektion mit fuenf Einheiten neu gebaut — und er spielte die
    # alte Ablehnung wieder ab, weil der Arbeitsordner schon dastand.
    frisch: list[str] = []
    alt_ordner = pfade.PODCAST_ARBEIT / (kopffeld(datei, "auftrag") or "")
    for kandidat in (pfade.PODCAST_ARBEIT).glob("*"):
        if not (kandidat / "auftrag.json").is_file():
            continue
        import sys
        if str(REPO) not in sys.path:
            sys.path.insert(0, str(REPO))
        from podcast.eintragen import passt
        # Gleicher Titel, andere Einheiten: das Skript ist ueberholt.
        if kandidat.name.startswith(_kurzname(titel)) and passt(datei, kandidat):
            frisch = ["--neues-skript"]
            break

    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w", encoding="utf-8") as f:
        if frisch:
            f.write("[Skript wird neu erzeugt: das vorhandene gilt anderem Material]\n")
        fertig = subprocess.run(
            [PYTHON, "-m", "podcast.bauen",
             "--einheiten", str(einheiten), "--titel", titel,
             "--nur", nur.replace(" ", ""), "--echte-vertonung", *frisch],
            cwd=str(REPO), stdout=f, stderr=subprocess.STDOUT, timeout=ZEIT_SKRIPT).returncode
        if fertig != 0:
            return fertig
        # **Bauen ist nicht fertig.** Am 12.09.2026 lagen vier vertonte Folgen
        # im Arbeitsverzeichnis, und alle vier Lektionen sagten weiter
        # `dauer_sek: 600` und nannten keine Tondatei: In der App war jede
        # Lektion genau 10:00 lang und keine spielte. Der Eintrag gehoert an
        # den Bau, nicht in eine zweite Handbewegung.
        f.write("\n--- Eintragen in die Lektion ---\n")
        f.flush()
        return subprocess.run(
            [PYTHON, "-m", "podcast.eintragen", "--alle"],
            cwd=str(REPO), stdout=f, stderr=subprocess.STDOUT, timeout=300).returncode


def tu_mindmap_analyse(log: Path, kapitel: str) -> int:
    prompt = f"""Du fuehrst den Auftrag {REPO}/auftraege/mindmap-analyse.md aus,
fuer Kapitel **{kapitel}**.

Arbeitsverzeichnis: {WISSEN}

Das Kapitel umfasst **alle** Lektionen aus kapitel/{kapitel}.md. Liegt
mindmap/{kapitel}.md schon vor, ersetze sie, statt sie zu ergaenzen.

Lies alle Lektionen des Kapitels (eingang/*/lektionen/) und alle darin
genannten Wissenseinheiten. Schreib die Analyse nach mindmap/{kapitel}.md.

Nimm so viele Achsen, wie die Sache verlangt, aber hoechstens neun und halte
jede Achse unter sieben Knoten (MMP-10a). Wenn du davon abweichst, begruende
es im Abschnitt Layout.

{SPARSAM}
Sprache: Deutsch."""
    code = claude(prompt, cwd=WISSEN, log=log, zeit=ZEIT_MODELL,
                  modell=MODELL["mindmap-analyse"])
    # **Ein hoeflicher Rueckzug ist kein Erfolg.** Am 12.09.2026 hat ein Agent
    # begruendet abgelehnt, weil ihm die Gliederung fehlte, und `claude -p`
    # endete mit 0 — die Warteschlange buchte die Aufgabe als erledigt.
    # Geprueft wird der Ertrag, nicht der Rueckgabewert.
    ziel = WISSEN / "mindmap" / f"{kapitel}.md"
    if code == 0 and not ziel.is_file():
        with log.open("a", encoding="utf-8") as f:
            f.write(f"\nKEIN ERTRAG: {ziel} wurde nicht geschrieben.\n")
        return 93
    return code


TUN = {
    "recherche-kapitel": tu_recherche,
    "wissen": tu_wissen,
    "pruefung": tu_pruefung,
    "podcast": tu_podcast,
}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--plan", action="store_true", help="nur zeigen, nichts tun")
    p.add_argument("--selbsttest", action="store_true",
                   help="alle Vorbereitungen durchlaufen, ohne eine Aufgabe zu starten")
    p.add_argument("--nur", default=None, metavar="K-nn",
                   help="nur dieses Kapitel arbeiten (fuer eine saubere Messung)")
    args = p.parse_args()

    if args.selbsttest:
        # `--plan` kehrt vor der Zugangspruefung zurueck und hat deshalb am
        # 12.09.2026 einen fehlenden Namen nicht gesehen, an dem die Unit dann
        # im Kreis neu startete. Dieser Weg laeuft alles an, was `main` anlaeuft.
        fehlt = lade_zugaenge()
        liste = aufgaben()
        schloss = nimm_das_schloss()
        for name, wert in [
            ("Zugaenge", "vollstaendig" if not fehlt else "FEHLT: " + ", ".join(fehlt)),
            ("Aufgaben", f"{len(liste)} aus {len(kapitel_aus_der_bibliothek())} Kapiteln"),
            ("Fenster", f"{FENSTER} Uhr, gerade " + ("offen" if im_fenster() else "zu")),
            ("Speicher", f"{frei_mb()} MB frei, {MIN_FREI_MB} noetig"),
            ("Schloss", "frei" if schloss else "haelt gerade jemand"),
            ("Grenzerkennung", "ja" if GRENZE_ERKANNT.search("session limit") else "NEIN"),
            ("Modelle", " · ".join(f"{k.split('-')[0]}={v}" for k, v in MODELL.items())),
        ]:
            print(f"  {name:16s} {wert}")
        return 0 if not fehlt else 2

    liste = aufgaben()
    stand = lies_stand()

    if args.plan:
        for auf in liste:
            zeichen = "erledigt" if stand["erledigt"].get(auf["id"]) else "offen"
            print(f"  {auf['id']:22s} {zeichen}")
        return 0

    LOGS.mkdir(parents=True, exist_ok=True)
    protokoll = ARBEIT / "nachtlauf.log"

    def schreib(text: str) -> None:
        zeile = f"{jetzt()}  {text}"
        print(zeile, flush=True)
        with protokoll.open("a", encoding="utf-8") as f:
            f.write(zeile + "\n")

    schloss = nimm_das_schloss()
    if schloss is None:
        print("Eine Warteschlange laeuft bereits. Zwei nebeneinander verbietet "
              "AUF-10 — dieser Lauf endet.", flush=True)
        return 0

    fehlt = lade_zugaenge()
    if fehlt:
        # Die Laeufe bis zur Vertonung wuerden trotzdem durchgehen. Sie
        # trotzdem zu starten hiesse, den Fehler erst in Stunden zu zeigen.
        schreib("ABBRUCH: keine Vertonung moeglich, es fehlen " + ", ".join(fehlt))
        schreib("Erwartet in .env oder in der Umgebung (siehe .env.example).")
        return 2

    schreib(f"Nachtlauf beginnt, {len(liste)} Aufgaben")


    if args.nur:
        liste = [a for a in liste if a.get("kapitel") == args.nur]
        schreib(f"Eingegrenzt auf {args.nur}: {len(liste)} Aufgaben")

    offen = list(liste)
    versuche: dict[str, int] = {}
    while offen:
        auf = offen.pop(0)
        if stand["erledigt"].get(auf["id"], {}).get("code") == 0:
            continue
        versuche[auf["id"]] = versuche.get(auf["id"], 0) + 1
        if versuche[auf["id"]] > 3:
            schreib(f"{auf['id']}: dreimal versucht, wird liegen gelassen")
            stand["erledigt"][auf["id"]] = {"code": 1, "grund": "dreimal gescheitert",
                                            "wann": jetzt()}
            schreib_stand(stand)
            continue
        # Folge und Abbildung brauchen eine Lektion. Fehlt sie, weil das
        # Wissen nicht zustande kam, wird uebersprungen statt abgebrochen.
        if auf["art"] in ("podcast", "abbildung") and not lektion_da(auf["abschnitt"]):
            schreib(f"{auf['id']}: uebersprungen, keine Lektion fuer {auf['abschnitt']}")
            stand["erledigt"][auf["id"]] = {"code": 90, "grund": "keine Lektion",
                                            "wann": jetzt()}
            schreib_stand(stand)
            continue

        modell = MODELL.get(auf["art"], "—")
        # **Das Fenster schuetzt die Claude-Kontingent** — es gilt deshalb nur
        # fuer Aufgaben, die daraus ziehen. Vertonung und Gegenprobe laufen
        # ueber ChatGPT und Azure; sie tagsueber warten zu lassen waere eine
        # Einschraenkung ohne Gewinn.
        if modell in LEITER:
            warte_aufs_fenster(schreib)
        warte_auf_speicher(schreib)
        for _ in range(versuche[auf["id"]] - 1):
            modell = hoeher(modell)
        schreib(f"{auf['id']}: beginnt ({modell}, Versuch {versuche[auf['id']]})")
        log = LOGS / f"{auf['id']}.log"
        begonnen = time.time()
        # Der Zeitpunkt wird gebraucht, um den Verbrauch zuzuordnen: Weil nur
        # ein Lauf zur Zeit arbeitet (AUF-10), ist das Zeitfenster eindeutig.
        begonnen_um = jetzt()
        try:
            kap = auf.get("kapitel")
            if auf["art"] == "mindmap-analyse":
                code = tu_mindmap_analyse(log, kap)
            else:
                fn = TUN[auf["art"]]
                code = (fn(auf["abschnitt"], log, kap, modell)
                        if auf["art"] == "recherche-kapitel"
                        else fn(auf["abschnitt"], log, kap))
        except subprocess.TimeoutExpired:
            code = 124
        except Exception as fehler:                      # noqa: BLE001
            schreib(f"{auf['id']}: {type(fehler).__name__}: {fehler}")
            code = 1
        dauer = int(time.time() - begonnen)

        # **Eine zugeschlagene Tuer ist kein Fehlschlag.** Steht im Log, dass
        # das Kontingent erschoepft ist, wird die Aufgabe nicht gebucht,
        # sondern gewartet und noch einmal versucht. Sonst rennt die
        # Warteschlange durch alles Uebrige und haelt am Morgen 31 Aufgaben
        # fuer gescheitert, die nie gelaufen sind (12.09.2026).
        text = log.read_text(encoding="utf-8", errors="replace")[-4000:] if log.is_file() else ""
        if code != 0 and GRENZE_ERKANNT.search(text):
            wieder = wann_wieder(text) or (datetime.now().astimezone() + timedelta(minutes=30))
            warten = max(60, int((wieder - datetime.now().astimezone()).total_seconds()) + 120)
            schreib(f"{auf['id']}: Kontingent erschoepft. Wartet bis "
                    f"{wieder:%H:%M} ({warten // 60} min) und versucht es erneut.")
            stand["wartet_bis"] = wieder.isoformat(timespec="seconds")
            schreib_stand(stand)
            time.sleep(warten)
            stand.pop("wartet_bis", None)
            offen.append(auf)                # noch einmal hinten anstellen
            schreib(f"{auf['id']}: wieder eingereiht")
            continue

        stand["erledigt"][auf["id"]] = {
            "code": code, "sek": dauer, "wann": jetzt(),
            "begonnen": begonnen_um, "modell": modell, "art": auf["art"],
        }
        schreib_stand(stand)
        schreib(f"{auf['id']}: Code {code} nach {dauer // 60} min ({modell})")

        # Der Index wird nach jedem Wissensschritt neu gebaut — er ist
        # Wegwerfware (BIB-18b), und so sieht der Dienst den Fortschritt
        # sofort statt erst am Morgen.
        if code == 0:
            sichere(auf["id"], schreib)
            subprocess.run([PYTHON, "-m", "bibliothek.index"],
                           cwd=str(REPO), capture_output=True, timeout=600)

    schreib("Nachtlauf fertig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
