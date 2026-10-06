"""TeachBuddy mit einem Befehl starten.

    python start.py              # Index bauen (falls nötig), Dienst und App starten
    python start.py --audio      # vorher die Podcast-Folgen herunterladen (~20 MB)
    python start.py --neu        # Index in jedem Fall neu bauen
    python start.py --pruefen    # zeigt, was installiert ist und was fehlt

Danach läuft die App unter http://127.0.0.1:5089/. Strg+C beendet beides.
Alle Einstellungen stehen in ``.env`` (Vorlage: ``.env.example``).
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import pfade

# Zeilenweise ausgeben, auch wenn die Ausgabe in eine Datei geht.
sys.stdout.reconfigure(line_buffering=True)

REPO = pfade.REPO
AUDIO_URL = os.environ.get(
    "TEACHBUDDY_AUDIO_URL",
    "https://github.com/niclaseschner-ship-it/teachbuddy/releases/latest/download/audio.zip")


def index_bauen(neu: bool) -> None:
    if pfade.INDEX.is_file() and not neu:
        alter = max((p.stat().st_mtime for p in pfade.WISSEN.rglob("*.md")), default=0)
        if pfade.INDEX.stat().st_mtime >= alter:
            return
    print(f"Index wird gebaut: {pfade.WISSEN} → {pfade.INDEX}", flush=True)
    subprocess.run([sys.executable, "-m", "bibliothek.index", "--still"], cwd=REPO, check=True)


def audio_holen() -> None:
    ziel = pfade.WISSEN / "audio"
    print(f"Lade Podcast-Folgen von {AUDIO_URL} …")
    with urllib.request.urlopen(AUDIO_URL, timeout=120) as antwort:
        daten = antwort.read()
    with zipfile.ZipFile(io.BytesIO(daten)) as zf:
        namen = [n for n in zf.namelist() if n.endswith(".mp3")]
        ziel.mkdir(parents=True, exist_ok=True)
        for name in namen:
            (ziel / Path(name).name).write_bytes(zf.read(name))
    print(f"{len(namen)} Folgen nach {ziel}")


def pruefen() -> int:
    """Was ist da, was fehlt — getrennt nach dem, wofür man es braucht."""
    def befehl(name: str, *args: str) -> str | None:
        pfad = os.environ.get("TEACHBUDDY_CODEX") if name == "codex" else None
        pfad = pfad or shutil.which(name)
        if not pfad:
            return None
        try:
            aus = subprocess.run([pfad, *args], capture_output=True, text=True, timeout=20)
            return (aus.stdout or aus.stderr).strip().splitlines()[0][:60] if aus.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            return None

    def gesetzt(*namen: str) -> bool:
        return all(os.environ.get(n) for n in namen)

    zeilen = [
        ("Lernen", "Python ≥ 3.10", sys.version_info >= (3, 10), sys.version.split()[0]),
        ("Lernen", "Flask", importlib.util.find_spec("flask") is not None, ""),
        ("Lernen", "Bibliothek", (pfade.WISSEN / "kapitel").is_dir(), str(pfade.WISSEN)),
        ("Lernen", "Podcast-Audio", (pfade.WISSEN / "audio").is_dir(), "python start.py --audio"),
        ("Gespräch", "TEACHBUDDY_OPENAI_API_KEY", gesetzt("TEACHBUDDY_OPENAI_API_KEY")
         or gesetzt("OPENAI_API_KEY"), "OpenAI Realtime"),
        ("Netz", "Zugangscode", os.environ.get("TEACHBUDDY_APP_HOST", "127.0.0.1")
         in ("127.0.0.1", "localhost") or gesetzt("TEACHBUDDY_ZUGANGSCODE"),
         "nötig, sobald TEACHBUDDY_APP_HOST nicht lokal ist"),
        ("Werkstatt", "claude (Claude Code)", befehl("claude", "--version"), "Recherche, Wissen"),
        ("Werkstatt", "codex (Codex CLI)", befehl("codex", "--version"), "Gegenprobe, Skript, Bild"),
        ("Werkstatt", "ffmpeg", befehl("ffmpeg", "-version"), "Folgen zusammenfügen"),
        ("Werkstatt", "Azure TTS", gesetzt("TEACHBUDDY_AZURE_OPENAI_ENDPOINT", "TEACHBUDDY_AZURE_OPENAI_KEY",
                                          "TEACHBUDDY_AZURE_OPENAI_DEPLOYMENT"), "Vertonung"),
        ("Werkstatt", "openai, pillow", importlib.util.find_spec("openai") is not None
         and importlib.util.find_spec("PIL") is not None, 'pip install -e ".[studio]"'),
    ]
    print(f"\n  {'':10} {'':28} {'':4} Hinweis")
    for bereich, was, ok, hinweis in zeilen:
        zeichen = "ok" if ok else "–"
        if isinstance(ok, str):
            hinweis = ok
        print(f"  {bereich:10} {was:28} {zeichen:4} {hinweis}")
    print("\n  Lernen braucht nur die oberen Zeilen. Fürs Gespräch den OpenAI-Schlüssel,")
    print("  für eigene Lernpfade die Werkstatt (docs/eigener-lernpfad.md).\n")
    return 0


def warte_auf(url: str, sekunden: int = 20) -> bool:
    ende = time.time() + sekunden
    while time.time() < ende:
        try:
            with urllib.request.urlopen(url, timeout=2) as antwort:
                json.load(antwort)
                return True
        except Exception:  # noqa: BLE001
            time.sleep(0.3)
    return False


def main() -> int:
    p = argparse.ArgumentParser(description="TeachBuddy starten")
    p.add_argument("--audio", action="store_true", help="Podcast-Folgen herunterladen")
    p.add_argument("--neu", action="store_true", help="Index in jedem Fall neu bauen")
    p.add_argument("--pruefen", action="store_true", help="Voraussetzungen anzeigen und enden")
    a = p.parse_args()

    if a.pruefen:
        return pruefen()

    if a.audio:
        audio_holen()
    index_bauen(a.neu)

    port = os.environ.get("TEACHBUDDY_PORT", "5088")
    app_port = os.environ.get("TEACHBUDDY_APP_PORT", "5089")
    umgebung = {**os.environ, "TEACHBUDDY_DIENST": f"http://127.0.0.1:{port}"}
    dienst = subprocess.Popen([sys.executable, "-m", "dienst.app"], cwd=REPO, env=umgebung)
    if not warte_auf(f"http://127.0.0.1:{port}/api/zustand"):
        dienst.terminate()
        print("Der Dienst ist nicht hochgekommen (siehe Ausgabe oben).", file=sys.stderr)
        return 1
    app = subprocess.Popen([sys.executable, "-m", "app.server"], cwd=REPO, env=umgebung)
    host = os.environ.get("TEACHBUDDY_APP_HOST", "127.0.0.1")
    print(f"\n  TeachBuddy läuft: http://{'127.0.0.1' if host == '0.0.0.0' else host}:{app_port}/\n")
    if not (pfade.WISSEN / "audio").is_dir():
        print("  Ohne Podcast-Audio. Mit `python start.py --audio` holen.\n")

    def beenden(*_):
        for proz in (app, dienst):
            proz.terminate()
    signal.signal(signal.SIGTERM, beenden)
    try:
        while dienst.poll() is None and app.poll() is None:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        beenden()
    return 0


if __name__ == "__main__":
    sys.exit(main())
