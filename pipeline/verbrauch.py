"""Wer frisst was — Verbrauch je Aufgabe, Modell und Schritt.

**Woher die Zahlen kommen.** Claude Code schreibt je Sitzung eine Mitschrift
nach ``~/.claude/projects/<projekt>/<id>.jsonl``, und jede Antwort darin trägt
ihren Verbrauch. Das ist gemessen, nicht geschätzt.

**Wie zugeordnet wird.** Die Warteschlange hält je Aufgabe fest, wann sie
begann und endete. Weil immer nur **ein** Lauf arbeitet (AUF-10), ist das
Zeitfenster eindeutig: Was in ihm verbraucht wurde, gehört zu dieser Aufgabe.
Ohne diese Regel wäre die Zuordnung nicht möglich.

Was nicht in ein Fenster fällt, ist die eigene Arbeit am Rechner. Sie wird
getrennt ausgewiesen, nicht weggelassen — sie zieht aus demselben Kontingent.

Aufruf::

    python3 -m pipeline.verbrauch              # seit heute früh
    python3 -m pipeline.verbrauch --seit 2026-09-11
    python3 -m pipeline.verbrauch --je-aufgabe # jede Aufgabe einzeln
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pfade  # noqa: E402

STAND = pfade.ARBEIT / "pipeline" / "stand.json"
MITSCHRIFTEN = os.path.expanduser("~/.claude/projects/*/*.jsonl")

# Richtpreise je Million Token (Stand 09/2026), nur zum Einordnen. Bezahlt
# wird über das Abo; die Zahl sagt, was die Arbeit auf dem freien Markt
# kostete — und damit, ob der Griff zum großen Modell sich gelohnt hat.
# Geprueft am 13.09.2026 gegen die Anbieterpreise. Meine erste Tabelle hatte
# Opus mit 15/75 angesetzt — das war die Preisklasse aelterer Opus-Generationen
# und **dreimal zu hoch**. Alle USD-Zahlen vom 12.09. waren entsprechend
# ueberhoeht.
#
# Cache-Lesen kostet 10 % des Eingabepreises.
PREIS = {          # (Eingabe, Cache-Lesen, Ausgabe) je Million Token
    "fable":  (10.00, 1.00, 50.00),
    "opus":   (5.00, 0.50, 25.00),
    "sonnet": (3.00, 0.30, 15.00),
    "haiku":  (1.00, 0.10, 5.00),
}


def _zeit(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone()
    except Exception:
        return None


def fenster() -> list[dict]:
    """Die Zeitfenster der Aufgaben, aus stand.json."""
    if not STAND.is_file():
        return []
    raus = []
    for name, v in json.loads(STAND.read_text(encoding="utf-8"))["erledigt"].items():
        ende = _zeit(v.get("wann", ""))
        if ende is None:
            continue
        beginn = _zeit(v["begonnen"]) if v.get("begonnen") else ende - timedelta(
            seconds=v.get("sek") or 0)
        raus.append({"id": name, "art": v.get("art") or name.split("-")[0],
                     "modell": v.get("modell", "?"), "code": v.get("code"),
                     "von": beginn, "bis": ende, "modelle": set(),
                     "ein": 0, "cache_neu": 0, "cache_lese": 0, "aus": 0, "rufe": 0})
    raus.sort(key=lambda x: x["von"])
    return raus


def sammeln(seit: datetime) -> tuple[list[dict], dict]:
    kaesten = fenster()
    # Nach Projekt getrennt: die eigene Arbeit ist nicht dasselbe wie ein
    # Agentenlauf, der aus dem Zeitraster gefallen ist.
    frei: dict[str, dict] = defaultdict(
        lambda: {"ein": 0, "cache_neu": 0, "cache_lese": 0, "aus": 0, "rufe": 0,
                 "modelle": set()})

    for datei in glob.glob(MITSCHRIFTEN):
        if datetime.fromtimestamp(os.path.getmtime(datei)).astimezone() < seit:
            continue
        for zeile in open(datei, encoding="utf-8", errors="replace"):
            try:
                d = json.loads(zeile)
            except Exception:
                continue
            wann = _zeit(d.get("timestamp", ""))
            u = (d.get("message") or {}).get("usage")
            if wann is None or wann < seit or not u:
                continue
            ziel = next((k for k in kaesten if k["von"] <= wann <= k["bis"]), None)
            topf = ziel if ziel is not None else frei[os.path.basename(os.path.dirname(datei))]
            # **Das Modell wird gemessen, nicht angenommen.** Genau daran ist
            # am 12.09.2026 monatelang unbemerkt Opus gelaufen, wo Haiku
            # gereicht haette.
            m = (d.get("message") or {}).get("model")
            if m and not m.startswith("<"):   # <synthetic> ist kein Modell
                topf["modelle"].add(m.replace("claude-", "").split("-4")[0].split("-5")[0])
            topf["ein"] += u.get("input_tokens", 0)
            topf["cache_neu"] += u.get("cache_creation_input_tokens", 0)
            topf["cache_lese"] += u.get("cache_read_input_tokens", 0)
            topf["aus"] += u.get("output_tokens", 0)
            topf["rufe"] += 1
    return kaesten, frei


def _modell(topf: dict, rueckfall: str = "opus") -> str:
    m = sorted(topf.get("modelle") or [])
    return "+".join(m) if m else rueckfall


def euro(topf: dict, modell: str) -> float:
    # Bei gemischten Modellen das teuerste — lieber zu hoch schaetzen als zu
    # niedrig, sonst sieht ein Lauf guenstiger aus, als er war.
    teile = [PREIS[x] for x in str(modell).split("+") if x in PREIS] or [PREIS["opus"]]
    ein, lese, aus = max(teile)
    return ((topf["ein"] + topf["cache_neu"]) * ein
            + topf["cache_lese"] * lese
            + topf["aus"] * aus) / 1_000_000


def zeile(name: str, t: dict, modell: str, breit: int = 22) -> str:
    gesamt = t["ein"] + t["cache_neu"] + t["cache_lese"] + t["aus"]
    return (f"  {name[:breit]:<{breit}s} {str(modell)[:6]:<6s} {t['rufe']:>5d} "
            f"{gesamt/1e6:>8.1f}M {t['aus']/1000:>7.0f}k {euro(t, modell):>8.2f}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seit", default=datetime.now().strftime("%Y-%m-%d"))
    p.add_argument("--je-aufgabe", action="store_true")
    a = p.parse_args()
    seit = datetime.fromisoformat(a.seit).astimezone()

    kaesten, frei = sammeln(seit)
    kopf = f"  {'':22s} {'Modell':6s} {'Rufe':>5s} {'Token':>9s} {'Ausg.':>8s} {'~USD':>8s}"

    if a.je_aufgabe:
        print(f"\nJe Aufgabe seit {a.seit}\n{kopf}")
        for k in sorted(kaesten, key=lambda x: -(x["cache_lese"] + x["cache_neu"])):
            if k["rufe"]:
                print(zeile(k["id"], k, _modell(k)))

    # Nach Schritt
    je_art: dict[tuple, dict] = defaultdict(
        lambda: {"ein": 0, "cache_neu": 0, "cache_lese": 0, "aus": 0, "rufe": 0, "n": 0,
                 "modelle": set()})
    for k in kaesten:
        if not k["rufe"]:
            continue
        t = je_art[(k["art"], _modell(k))]
        t["modelle"] |= k["modelle"]
        for f in ("ein", "cache_neu", "cache_lese", "aus", "rufe"):
            t[f] += k[f]
        t["n"] += 1

    print(f"\nNach Schritt seit {a.seit}\n{kopf}")
    gesamt_usd = 0.0
    for (art, modell), t in sorted(je_art.items(), key=lambda x: -(x[1]["cache_lese"])):
        print(zeile(f"{art} ({t['n']}×)", t, modell))
        gesamt_usd += euro(t, modell)

    for projekt, t in sorted(frei.items(), key=lambda x: -x[1]["cache_lese"]):
        if t["rufe"]:
            name = projekt.rsplit("-", 1)[-1] or "Gespraech"
            print(zeile(f"ausserhalb: {name}", t, _modell(t)))
            gesamt_usd += euro(t, _modell(t))
    print(f"\n  Zusammen etwa {gesamt_usd:,.2f} USD Marktwert.")
    print("  Bezahlt ist es ueber die Abos — die Zahl sagt, ob der Griff zum")
    print("  grossen Modell sich gelohnt hat, nicht was abgebucht wurde.")

    # Was dabei herausgekommen ist
    fertig = [k for k in kaesten if k["code"] == 0 and k["art"] == "wissen"]
    if fertig:
        t = sum(k["cache_lese"] + k["cache_neu"] + k["aus"] for k in fertig)
        print(f"\n  Wissen: {len(fertig)} Laeufe, {t/1e6:.0f}M Token")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
