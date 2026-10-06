---
name: teachbuddy
description: >
  Installiert, richtet ein und betreibt TeachBuddy — von der ersten Installation
  über den eigenen Lernpfad bis zum Betrieb fürs Telefon. Klärt einmal die
  Rahmenbedingungen (Ziel, Rechner, Zugänge, Budget), führt durch Installation,
  Demo, eigene Bibliothek, Bau eines Lernpfads mit Agenten, Sichtung der Bilder,
  Prüfung und Freigabe, Dauerbetrieb, Updates und Fehlersuche. Auslöser:
  "installier TeachBuddy", "richte das ein", "ich will einen eigenen Lernpfad",
  "bau mir einen Kurs zu …", "starte die App", "aufs Handy", "läuft nicht",
  "update", "Beanstandungen einarbeiten", "Bilder neu machen".
---

# TeachBuddy einrichten und betreiben

Du führst einen Menschen durch TeachBuddy. Er soll am Ende **eigene Lernpfade**
bauen und unterwegs lernen können. Die mitgelieferte Bibliothek unter `demo/`
ist nur das Anschauungsstück.

Arbeite im Repo-Wurzelverzeichnis. Halte dich an die vier Regeln in
`CONTRIBUTING.md` — besonders: nichts erfinden, wo etwas offen ist.

## 0. Wo stehen wir?

Immer zuerst:

```bash
python start.py --pruefen        # was installiert ist und was fehlt
cat arbeit/rahmen.md 2>/dev/null # was beim letzten Mal geklärt wurde
```

Ist `arbeit/rahmen.md` da, frag nicht alles noch einmal. Spring zu dem
Abschnitt, um den es geht.

## 1. Rahmenbedingungen klären — einmal

Frag in **einer** Runde, knapp, mit Vorschlägen statt offener Fragen:

1. **Ziel:** nur die Demo ansehen · eigene Lernpfade bauen · beides
2. **Wo lernen:** nur an diesem Rechner · auch am Telefon im WLAN · auch
   unterwegs
3. **Rechner:** Betriebssystem, Arbeitsspeicher, läuft er dauerhaft?
   (Ein Raspberry Pi mit 8 GB genügt.)
4. **Zugänge:** Was ist vorhanden?
   - Claude Code (Abo oder Anthropic-API-Schlüssel) → Recherche, Wissen, Mindmap
   - Codex CLI (ChatGPT-Abo oder OpenAI-API-Schlüssel) → Gegenprobe, Podcast-Skript, Bilder
   - OpenAI-API-Schlüssel → Gesprächspartner (**ohne geht das Gespräch nicht**)
   - Azure OpenAI mit TTS-Deployment → Vertonung der Folgen
5. **Budget:** Das Gespräch kostet grob 0,50–0,70 $ je zehn Minuten, die
   Vertonung einer Folge wenige Cent. Die Agenten laufen über die Abos und
   verbrauchen viel Kontingent (ein Kapitel: mehrere Stunden).

Schreib das Ergebnis nach `arbeit/rahmen.md` (Stichpunkte, Datum). Diese Datei
liegt nicht im Git.

### Fehlt ein Baustein? Dann umbauen statt aufgeben

TeachBuddy ist auf Austausch angelegt (TB-7): Kein Modul spricht direkt mit
einem Anbieter. Biete den Umbau an, wenn etwas fehlt, und mach ihn mit dem
Menschen zusammen:

| fehlt | wo umbauen | Hinweis |
|---|---|---|
| Azure | `podcast/vertonung.py` (`AzureVertonung`, `aus_umgebung`) | Gleiche Schnittstelle `synthese(text, voice)` mit OpenAI-TTS (`client.audio.speech.create`) oder einem anderen Dienst; `STIMMEN` anpassen; Tests in `podcast/test_podcast.py` |
| Claude Code | `pipeline/nachtlauf.py` (`claude()`) | Dieselben Aufträge aus `auftraege/` über `codex exec` laufen lassen. Dann prüft dasselbe Modell, was es geschrieben hat — die Gegenprobe verliert an Wert (AUF-16); das offen sagen |
| Codex | `podcast/skript.py` (`rufe_agenten`), `pipeline/nachtlauf.py` (`tu_pruefung`), `pipeline/lektionsbild/bauen.sh` | Skript und Gegenprobe über `claude -p`; Lektionsbilder brauchen dann ein anderes Bildmodell oder entfallen |
| OpenAI-Schlüssel | — | Kein Gespräch. Alles andere läuft. |

Ein Umbau ändert Verhalten: Spec im selben Schritt anpassen (`specs/constitution.md`
TB-5/TB-7, `specs/formate/…`), Tests grün halten, dem Menschen zeigen.

## 2. Installieren

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                 # Lernen und Tests
pip install -e ".[studio]"              # nur für eigene Lernpfade
cp .env.example .env                    # dann ausfüllen, siehe unten
python -m pytest -q                     # muss grün sein
```

Für die Werkstatt zusätzlich: `ffmpeg` (Paketmanager), `claude` und `codex`
installiert **und angemeldet** — beides selbst einmal aufrufen lassen
(`claude`, `codex login`). Danach wieder `python start.py --pruefen`.

**`.env` füllst du nie mit Werten, die du dir ausdenkst.** Frag nach den
Schlüsseln oder lass den Menschen sie selbst eintragen. `.env` kommt nie ins Git.

## 3. Demo zeigen

```bash
python start.py --audio      # lädt beim ersten Mal die Folgen
```

`http://127.0.0.1:5089/` öffnen lassen. Zeig: Lektion mit Folge und Bild →
Übersichtsfolie mit Belegen → Kapitel mit Mindmap → (mit Schlüssel) Gespräch.
Zeig auch `demo/pruefung/K-03-1.md`: So sieht eine Gegenprobe aus, und unten
steht, wie die Beanstandungen eingearbeitet wurden.

## 4. Eigene Bibliothek anlegen

```bash
python -m bibliothek.anlegen ~/teachbuddy-bibliothek --env
```

Sie liegt außerhalb dieses Repos und ist ein eigenes Git-Repo. Empfiehl ein
privates Remote als Sicherung (`git remote add …`). Ab jetzt zeigt die App
diese Bibliothek; zurück zur Demo: `TEACHBUDDY_WISSEN` in `.env` entfernen.

## 5. Einen Lernpfad entwerfen — mit dem Menschen

Das ist ein Gespräch, kein Auftrag an die Pipeline. Leitfaden:
`auftraege/curriculum.md`, Vorlagen: `docs/eigener-lernpfad.md`.

1. Frag nach **Ziel und Vorwissen** (wer lernt, was kann er schon, was will er
   danach können) und nach dem Umfang (ein Kapitel zum Ausprobieren ist ein
   guter Anfang: 4–8 Lektionen).
2. Schlag die Abschnitte vor — je Lektion ein Titel, der eine **Frage
   beantwortet**, und zwei, drei Sätze, was dort gelernt wird. Die Recherche
   richtet sich danach.
3. Schreib `pfade/P-01.md` und `kapitel/K-01.md` erst, wenn der Mensch zustimmt.
   Lass ihn committen.

## 6. Bauen lassen

```bash
python -m pipeline.nachtlauf --plan
TEACHBUDDY_FENSTER=0-24 nohup python -m pipeline.nachtlauf --nur K-01 > arbeit/lauf.txt 2>&1 &
```

- Läuft Stunden, ein Schritt nach dem anderen: Recherche → Wissen → Gegenprobe →
  Podcast → Mindmap-Analyse. Fortschritt: `arbeit/pipeline/nachtlauf.log`,
  je Schritt `arbeit/pipeline/logs/<aufgabe>.log`.
- Standard-Zeitfenster ist 21–8 Uhr, weil die Agenten aus dem Abo-Kontingent
  des Menschen ziehen. Frag, ob er tagsüber selbst damit arbeitet.
- Ist das Kontingent erschöpft, wartet die Warteschlange bis zur gemeldeten
  Uhrzeit. Das ist kein Fehler.
- Nach jedem gelungenen Schritt committet sie in der Bibliothek — das ist
  Sicherung, **keine** Freigabe.
- Verweigert der Skript-Agent eine Folge („Ablehnung: …"), ist das meist
  berechtigt: Der Lektionstitel verspricht, was das Material nicht trägt.
  Dann Titel ehrlich machen oder nachrecherchieren lassen — nicht erzwingen.

## 7. Lektionsbilder malen und **ansehen**

```bash
pipeline/lektionsbild/alle.sh          # je Bild ~3 Minuten, über Codex
```

Sieh **jedes** Bild selbst an (`arbeit/lektionsbild/<L>/bild.png`) und lies
es gegen `material.md` daneben. Etwa jedes achte Bild hat einen Fehler, den
das Bildmodell bei seiner eigenen Prüfung übersieht:

- verzerrte oder falsch geschriebene Wörter, auch im Untertitel
- ein dunkler Schleier oder Verlauf über Titel und Kernaussage
- Logos, Marken, Produktnamen
- Zahlen, Beispiele oder Wörter, die nicht im Material stehen

Fehlerhafte neu malen: `pipeline/lektionsbild/bauen.sh L-…`. Hält `alle.sh`
mit „Kontingent leer" an, später fortsetzen — es überspringt nichts, was schon
ein Bild hat.

## 8. Prüfen und freigeben

Die Freigabe gibt der Mensch. Du bereitest sie so vor, dass er nur noch
entscheiden muss:

1. `python -m bibliothek.befunde` — Fehler müssen weg; `absatz_ohne_marker`
   heißt, ein Absatz steht ohne Beleg und ohne `[E]` auf der Folie.
2. **Die Gegenprobe abarbeiten** (`pruefung/K-01-*.md`). Für jede Beanstandung:
   - an der **Primärquelle** nachprüfen (abrufen, nicht aus dem Gedächtnis);
   - trifft sie zu: neue Fundstelle mit dem abgerufenen Wortlaut in
     `quellen/Q-…/fundstellen.md`, Beleg korrigieren oder einen neuen anlegen,
     die Wissenseinheit neu fassen, die Lektionsübersicht nachziehen;
   - unten in der Prüfungsdatei unter `## NACHGEBESSERT` festhalten, was wie
     erledigt wurde (Vorbild: `demo/pruefung/K-03-1.md`).
3. Betroffene Folgen neu bauen (Podcast-Schritt der Warteschlange erneut, oder
   `python -m podcast.bauen … --neues-skript --echte-vertonung` und
   `python -m podcast.eintragen <lektion.md> <ordner>`), betroffene Bilder neu malen.
4. `git diff` in der Bibliothek zeigen, Fragen beantworten — **committen lässt
   du den Menschen**.

## 9. Betreiben

**Starten:** `python start.py`. Fürs Telefon im WLAN in `.env`:
`TEACHBUDDY_APP_HOST=0.0.0.0` **und** `TEACHBUDDY_ZUGANGSCODE=<lang, zufällig>`;
das Telefon öffnet einmal `http://<rechner>:5089/?zugang=<code>`.
**Nie ohne Zugangscode ins Netz** — hinter der App liegen Wege, die Geld kosten.

**Installierbar und offline** wird die App erst über HTTPS. Wege, vom
einfachsten an: `tailscale serve 5089` (privates Netz), Caddy mit eigener
Domain, nginx mit Let's Encrypt. Auch dann den Zugangscode setzen.

**Dauerbetrieb (Linux, systemd als Benutzerdienst):**

```ini
# ~/.config/systemd/user/teachbuddy.service
[Unit]
Description=TeachBuddy
[Service]
WorkingDirectory=%h/teachbuddy
ExecStart=%h/teachbuddy/.venv/bin/python start.py
Restart=on-failure
[Install]
WantedBy=default.target
```

`systemctl --user enable --now teachbuddy` und `loginctl enable-linger $USER`,
damit er ohne Anmeldung läuft. macOS: ein LaunchAgent mit demselben Befehl.

**Sichern:** die Bibliothek (eigenes Git-Repo, Remote pushen) und
`arbeit/lernstand.db` (Fortschritt, Antworten, Gespräche). Alles andere unter
`arbeit/` ist wieder erzeugbar.

**Aktualisieren:** `git pull && pip install -e ".[studio]" && python -m pytest -q`,
dann neu starten. Die eigene Bibliothek bleibt davon unberührt.

## Wenn etwas nicht geht

| Zeichen | Ursache und Weg |
|---|---|
| App weiß, Meldung „Dienst nicht erreichbar" | Dienst läuft nicht: `python start.py` neu, Ausgabe lesen |
| Lektion ohne Ton | Audio fehlt: `python start.py --audio` (Demo) bzw. Podcast-Schritt |
| 401 im Browser | Zugangscode gesetzt: einmal `?zugang=<code>` an die Adresse |
| Gespräch startet nicht | `TEACHBUDDY_OPENAI_API_KEY` fehlt oder ohne Guthaben |
| Pipeline: „ABBRUCH: keine Vertonung möglich" | `TEACHBUDDY_AZURE_OPENAI_*` in `.env` fehlen |
| Skript-Agent scheitert mit 400 „requires a newer version" | Codex aktualisieren (`npm i -g @openai/codex`) |
| Alte Fassung im Browser | `neustart.html` öffnen — holt jede Datei neu |
