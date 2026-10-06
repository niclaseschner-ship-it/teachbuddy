"""Auslieferer der App — statische Dateien und Weiterleitung.

Kein Build-Schritt (E-5), also braucht die App nur jemanden, der die Dateien
herausgibt. Dieser Server tut drei Dinge und sonst nichts:

1. **Statisch** — alles aus ``app/`` so, wie es im Repo liegt.
2. **Weiterleiten** — jedes ``/api/…`` geht unverändert an den Dienst auf
   ``127.0.0.1:5088``. Damit spricht das Frontend nur den Datenvertrag, und es
   gibt keine zweite Wahrheit über die Daten.
3. **Zugang** — mit ``TEACHBUDDY_ZUGANGSCODE`` nur für Geräte, die den Code
   einmal mitgebracht haben.

Starten::

    python -m app.server                     # 127.0.0.1:5089
    TEACHBUDDY_APP_HOST=0.0.0.0 TEACHBUDDY_ZUGANGSCODE=… python -m app.server
"""

from __future__ import annotations

import hashlib
import hmac
import http.server
import json
import os
import socketserver
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pfade  # noqa: F401  — liest .env

HIER = Path(__file__).resolve().parent
DIENST = os.environ.get("TEACHBUDDY_DIENST", "http://127.0.0.1:5088")
PORT = int(os.environ.get("TEACHBUDDY_APP_PORT", "5089"))
# Standard: nur dieser Rechner. Fuers Telefon im WLAN `0.0.0.0` setzen — und
# dann einen Zugangscode, denn hinter der App liegen Wege, die Geld kosten
# (Sprachgespraech, Vertonung).
HOST = os.environ.get("TEACHBUDDY_APP_HOST", "127.0.0.1")
ZUGANGSCODE = os.environ.get("TEACHBUDDY_ZUGANGSCODE", "")
KEKS = "teachbuddy_zugang"

# Ohne Angabe die Übersicht: Sie ist die Landkarte, von der alles ausgeht.
STARTSEITE = "/uebersicht.html"

# Der Mantel: die Dateien, die zusammen eine Fassung ergeben. Aendert sich eine,
# aendert sich die Fassung, und der Service Worker wirft die alte ganz weg.
MANTEL = (
    "uebersicht.html", "d-lektion.html", "e-kapitel.html",
    "stil.css", "abspieler.css", "abspieler.js", "bildschau.js", "daten.js",
    "huelle.js", "zustand.js", "gespraech.js", "mindmap.js", "sw.js",
    "manifest.json", "neustart.html", "app-installieren.js",
)


class Ausliefern(http.server.SimpleHTTPRequestHandler):
    # http.server spricht sonst HTTP/1.0 — ohne Keep-Alive. Chrome registriert
    # Service Worker darueber unzuverlaessig (dann gibt es kein „installieren"),
    # und laufende Tonspuren brechen ab, weil jede Teilanfrage eine neue
    # Verbindung braucht. Beides ist am 11.09.2026 aufgetreten.
    protocol_version = "HTTP/1.1"

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HIER), **kw)

    # -- Fassung ------------------------------------------------------------

    def _fassung(self) -> str:
        """Eine Kennung, die sich aendert, sobald sich eine Manteldatei aendert.

        **Warum das kein Build-Schritt ist** (E-5): Sie wird aus den Dateien
        auf der Platte gerechnet, bei jeder Anfrage neu. Es gibt nichts zu
        erzeugen, nichts zu pflegen und nichts, das vergessen werden kann.

        **Wozu sie da ist:** Ohne Build heissen alle Dateien immer gleich.
        Damit kann ein Cache eine alte `daten.js` neben einer neuen
        `uebersicht.html` liefern, und ein ES-Modulimport bricht die Seite
        ohne Meldung ab (13.09.2026). Die Fassung macht den Mantel atomar.
        """
        h = hashlib.sha256()
        for name in sorted(MANTEL):
            datei = HIER / name
            if datei.is_file():
                h.update(name.encode())
                h.update(str(datei.stat().st_mtime_ns).encode())
                h.update(str(datei.stat().st_size).encode())
        return h.hexdigest()[:16]

    def _stand(self) -> bytes:
        """Der Rumpf von ``version.json``: die Fassung und der Mantel dazu.

        Die Dateiliste steht mit drin, damit `neustart.html` nicht wissen
        muss, woraus die App besteht. Es gibt genau eine Liste, ``MANTEL``
        hier oben, und wer aufraeumen will, fragt danach. Eine zweite Liste im
        Frontend waere genau die Sorte Doppelpflege, die irgendwann
        auseinanderlaeuft und dann eine Datei stehen laesst.
        """
        rumpf = {"fassung": self._fassung(), "mantel": list(MANTEL)}
        return json.dumps(rumpf, ensure_ascii=False).encode("utf-8")

    def guess_type(self, pfad):
        # Den Typ hier setzen und nicht in end_headers: Dort kaeme ein zweiter
        # Content-Type hinzu, und der Browser nimmt dann den erstgenannten.
        if str(pfad).endswith("manifest.json"):
            return "application/manifest+json"
        return super().guess_type(pfad)

    def end_headers(self):
        """Cache-Anweisungen. **Der Kern des Problems vom 13.09.2026.**

        Ohne `Cache-Control` sendet dieser Server nur `Last-Modified`. Jeder
        Browser wendet dann *heuristisches Caching* an: Er behaelt die Datei
        eine selbstgewaehlte Zeit und **fragt gar nicht erst nach**.

        Genau daran lag es, dass die App nur im Privatfenster lief. Nicht am
        Service Worker — am gewoehnlichen HTTP-Cache, den weder
        `neustart.html` noch ein Worker anfassen. Ein `?frisch=…` an der
        HTML-Adresse umgeht ihn fuer die Seite, nicht fuer ihre Module: Deren
        Adresse bleibt gleich. Frische Seite, alte Module, Import ins Leere.
        Ich habe zwei Tage lang den falschen Cache verdaechtigt.

        **`no-cache` heisst nicht „nicht speichern", sondern „vor dem
        Benutzen nachfragen".** Mit dem `Last-Modified` daneben ist das ein
        304 ohne Rumpf — ein paar hundert Byte, und nie falsch. Genau das
        braucht eine App ohne Build-Schritt, deren Dateien immer gleich
        heissen (E-5).
        """
        weg = self.path.split("?")[0]
        if weg.endswith("/version.json"):
            # Setzt sich selbst (`no-store`). Hier nichts hinzufuegen, sonst
            # steht Cache-Control zweimal in der Antwort.
            return super().end_headers()
        if weg.endswith((".html", ".js", ".css", ".json")) or weg.endswith("/"):
            self.send_header("Cache-Control", "no-cache")
        elif weg.endswith((".png", ".mp3", ".svg", ".ico")):
            # Unveraenderlich genug, und gross: eine Stunde ohne Rueckfrage.
            self.send_header("Cache-Control", "max-age=3600")
        super().end_headers()

    def log_message(self, format, *args):  # noqa: A002 - Signatur von http.server
        # Nur Fehler, sonst wird das Journal vom Abspielen zugemüllt.
        if args and str(args[1]).startswith(("4", "5")):
            super().log_message(format, *args)

    # -- Weiterleitung -----------------------------------------------------

    def _ist_api(self) -> bool:
        return self.path.startswith("/api/")

    def _weiterleiten(self, methode: str) -> None:
        laenge = int(self.headers.get("Content-Length") or 0)
        rumpf = self.rfile.read(laenge) if laenge else None
        anfrage = urllib.request.Request(DIENST + self.path, data=rumpf, method=methode)
        for name in ("Content-Type", "Range", "If-Range", "Accept"):
            wert = self.headers.get(name)
            if wert:
                anfrage.add_header(name, wert)
        try:
            with urllib.request.urlopen(anfrage, timeout=60) as antwort:
                self._durchreichen(antwort, methode)
        except urllib.error.HTTPError as fehler:
            self._durchreichen(fehler, methode)
        except urllib.error.URLError as fehler:
            # Ehrlich sein, statt eine leere Seite zu zeigen (TB-8).
            nachricht = ('{"fehler":"dienst_nicht_erreichbar","grund":"%s unter %s"}'
                         % (fehler.reason, DIENST)).encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(nachricht)))
            self.end_headers()
            self.wfile.write(nachricht)

    def _durchreichen(self, antwort, methode: str) -> None:
        koerper = b"" if methode == "HEAD" else antwort.read()
        self.send_response(antwort.status)
        for name, wert in antwort.headers.items():
            if name.lower() in ("transfer-encoding", "connection", "content-length"):
                continue
            self.send_header(name, wert)
        # HTTP/1.1 ohne Laengenangabe laesst den Browser auf das Ende warten,
        # das nie kommt. Deshalb wird der Koerper hier vollstaendig gelesen und
        # die Laenge gesetzt. Die Tonspur geht in Teilstuecken (Range), also
        # bleibt das je Anfrage klein.
        self.send_header("Content-Length", str(len(koerper)))
        self.end_headers()
        if koerper:
            self.wfile.write(koerper)

    # -- Zugang -------------------------------------------------------------

    def _zugang(self) -> bool:
        """Mit gesetztem ``TEACHBUDDY_ZUGANGSCODE`` braucht jede Anfrage den Keks.

        Einmal ``…/?zugang=<code>`` oeffnen, dann merkt sich das Geraet den
        Zugang ein Jahr lang. Ohne Code ist alles offen — dann sollte die App
        nur auf ``127.0.0.1`` lauschen (Standard).
        """
        if not ZUGANGSCODE:
            return True
        soll = hashlib.sha256(ZUGANGSCODE.encode()).hexdigest()
        weg, _, abfrage = self.path.partition("?")
        code = urllib.parse.parse_qs(abfrage).get("zugang", [""])[0]
        if code and hmac.compare_digest(code, ZUGANGSCODE):
            rest = urllib.parse.urlencode(
                [(k, v) for k, v in urllib.parse.parse_qsl(abfrage) if k != "zugang"])
            self.send_response(302)
            self.send_header("Set-Cookie", f"{KEKS}={soll}; Max-Age=31536000; "
                                           "Path=/; HttpOnly; SameSite=Lax")
            seite = weg.rsplit("/", 1)[-1] or STARTSEITE.lstrip("/")
            self.send_header("Location", f"./{seite}" + (f"?{rest}" if rest else ""))
            self.send_header("Content-Length", "0")
            self.end_headers()
            return False
        kekse = self.headers.get("Cookie", "")
        for teil in kekse.split(";"):
            name, _, wert = teil.strip().partition("=")
            if name == KEKS and hmac.compare_digest(wert, soll):
                return True
        rumpf = ("<!doctype html><meta charset='utf-8'><title>TeachBuddy</title>"
                 "<p style='font:16px system-ui;margin:2em'>Diese TeachBuddy-Instanz "
                 "braucht einen Zugangscode. Öffne die Adresse einmal mit "
                 "<code>?zugang=…</code> am Ende.</p>").encode("utf-8")
        self.send_response(401)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(rumpf)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(rumpf)
        return False

    # -- HTTP --------------------------------------------------------------

    def do_GET(self) -> None:  # noqa: N802
        if not self._zugang():
            return
        if self.path.split("?")[0].endswith("/version.json"):
            rumpf = self._stand()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(rumpf)))
            # Diese eine Datei darf nie aus einem Cache kommen — sie ist das
            # Mittel, mit dem Cache-Staende ueberhaupt erkannt werden.
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(rumpf)
            return
        if self._ist_api():
            return self._weiterleiten("GET")
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", "." + STARTSEITE)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._zugang():
            return
        if self._ist_api():
            return self._weiterleiten("HEAD")
        super().do_HEAD()

    def do_PUT(self) -> None:  # noqa: N802
        if self._zugang():
            self._weiterleiten("PUT") if self._ist_api() else self.send_error(405)

    def do_POST(self) -> None:  # noqa: N802
        if self._zugang():
            self._weiterleiten("POST") if self._ist_api() else self.send_error(405)


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    with Server((HOST, PORT), Ausliefern) as srv:
        print(f"App auf http://{HOST}:{PORT}/, Dienst unter {DIENST}", flush=True)
        if HOST not in ("127.0.0.1", "localhost", "::1") and not ZUGANGSCODE:
            print("WARNUNG: Die App ist im Netz erreichbar, aber ohne Zugangscode. "
                  "Setze TEACHBUDDY_ZUGANGSCODE.", flush=True)
        srv.serve_forever()


if __name__ == "__main__":
    main()
