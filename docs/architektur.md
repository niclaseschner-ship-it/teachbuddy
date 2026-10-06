# Wie TeachBuddy gebaut ist

## Das Bild im Großen

```
            ┌────────────── Erzeugung (selten, nachts) ──────────────┐
            │  pipeline/nachtlauf.py   claude -p · codex exec · Azure │
            │  pipeline/lektionsbild/  codex exec (image_gen)         │
            └──────────────────────────┬──────────────────────────────┘
                                       │ schreibt Dateien, ein Mensch committet
                                       ▼
   Bibliothek         Markdown mit Frontmatter: Quellen → Fundstellen → Belege
   (die Bibliothek)   → Wissenseinheiten → Lektionen, Kapitel, Lernpfade
                      + bilder/ + audio/
                                       │ python -m bibliothek.index
                                       ▼
   arbeit/index.db    SQLite mit Volltextsuche — wegwerfbar, jederzeit neu gebaut
                                       │
   dienst/  (Flask, 127.0.0.1:5088)  ──┤── arbeit/lernstand.db (Fortschritt,
                                       │   Antworten, Gespräche, Kosten)
   app/server.py (127.0.0.1:5089)    ──┤── statische Dateien + /api/… durchreichen
                                       ▼
   app/  (PWA)        Übersicht · Kapitel (Mindmap, Gespräch) · Lektion
                      (Abspieler, Bild, Folie, Belege, Fragen) — offline fähig
```

## Die Bibliothek ist die Wahrheit

Alles Wissen liegt als Datei in der Bibliothek — `demo/` oder einer eigenen (`python -m bibliothek.anlegen`) —, nicht in einer Datenbank
([E-9](../decisions/E-9.md)). Agenten schreiben Vorschläge als Dateien; ein
`git diff` zeigt, was sich ändern soll, ein Commit gibt frei (BIB-16, BIB-18a).

Die Kette von der Quelle zur Lektion ist durchgehend nachvollziehbar:

| Ebene | Datei | trägt |
|---|---|---|
| Quelle | `quellen/Q-…/quelle.md` | Titel, Urheber, Fundort, Abrufdatum, **Lizenz** |
| Fundstelle | `quellen/Q-…/fundstellen.md` | wörtliches Zitat und genaue Stelle |
| Beleg | `belege/B-….md` | die Aussage, die aus einer Fundstelle folgt, mit Zuversicht |
| Wissenseinheit | `einheiten/WE-….md` | ein lernbarer Gedanke: Stichwort, Kernaussage, Inhalt, Belege, Kanten |
| Lektion | `lektionen/L-….md` | welche Einheiten, Audio, Kapitelmarken, Bild |

Was keine Quelle trägt, ist im Text als Einordnung `[E]` markiert (TB-1). Die
Übersichtsfolie zeigt unbelegte Absätze sichtbar als solche (OBF-17).

`bibliothek/lesen.py` liest das alles streng ein — was vom Modell abweicht,
wird ein **Befund** und nicht still geschluckt. `bibliothek/index.py` baut
daraus `index.db` mit Volltextsuche und typisierten Kanten.

## Der Dienst

`dienst/app.py` ist ein Flask-Dienst ohne weitere Abhängigkeiten. Er liest nur
aus dem Index und schreibt nur in den Lernstand. Die Endpunkte stehen in
[`dienst/README.md`](../dienst/README.md); die wichtigste Eigenschaft: **Belege
reisen mit** der Lektion, ausgeschrieben, damit sie auch offline erreichbar
sind (R-5).

**Das Gespräch** läuft nicht über den Server, sondern direkt vom Browser zu
OpenAI Realtime (WebRTC). Der Dienst gibt dafür nur ein kurzlebiges Token aus
und legt die Wissenseinheiten des Kapitels samt Belegen als Kontext bei
([E-20](../decisions/E-20.md)). Der langlebige Schlüssel verlässt den Server
nie. Während des Gesprächs kann der Partner über vier Werkzeuge in der
Bibliothek nachschlagen, im Web recherchieren, einen Rechercheauftrag für
später aufnehmen und abhaken, welche Punkte geprüft sind.

## Die App

`app/` ist eine PWA ohne Framework und ohne Build-Schritt
([E-5](../decisions/E-5.md)): HTML, CSS und ES-Module. `app/server.py`
liefert die Dateien aus und reicht `/api/…` an den Dienst durch.

- **Offline:** `sw.js` hält die App und jede gesicherte Lektion samt Audio.
  Fortschritt, der offline entsteht, wird nachgereicht; bei Konflikten gewinnt
  der spätere Zeitpunkt.
- **Fassung:** Der Server rechnet aus den App-Dateien eine Fassungskennung.
  Ändert sich eine Datei, verwirft der Service Worker den alten Stand ganz —
  nie halb alt, halb neu.
- **Zugang:** Standardmäßig nur `127.0.0.1`. Im Netz nur mit
  `TEACHBUDDY_ZUGANGSCODE` (APP-8).

## Die Erzeugung

Zwei Modelle, getrennte Rollen ([AUF](../specs/aufbereitung.md)): Claude
recherchiert und modelliert, GPT prüft gegen und schreibt das Podcast-Skript —
ein Modell, das seinen eigenen Text prüft, findet den Fehler genau dort nicht,
wo er entstanden ist. Beide laufen über ihre Abo-CLIs (TB-5); bezahlt wird nur,
was der Lernende erlebt: die Sprachausgabe (Azure OpenAI) und das Gespräch.

Ein Podcast entsteht in `podcast/`: Skript aus den Wissenseinheiten, eine
Belegprobe gegen das Skript, Vertonung je Sprecherzeile mit Cache,
Zusammenfügen mit ffmpeg, Kapitelmarken aus den Überschriften. Die Fassung der
Pipeline wird an jeder Folge mitgeschrieben (AUF-18a).

## Wo was steht

| | |
|---|---|
| Prinzipien | [`specs/constitution.md`](../specs/constitution.md) |
| Bibliothek | [`specs/bibliothek.md`](../specs/bibliothek.md) |
| Agenten und Formate | [`specs/aufbereitung.md`](../specs/aufbereitung.md), [`specs/formate/`](../specs/formate/) |
| App und Oberfläche | [`specs/app.md`](../specs/app.md), [`specs/oberflaeche.md`](../specs/oberflaeche.md) |
| Entscheidungen | [`decisions/`](../decisions/) |
| Pfade und Einstellungen | [`pfade.py`](../pfade.py), [`.env.example`](../.env.example) |
