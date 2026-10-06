# Podcast-Bau — was aus dem Hörspiel-Vorbild geerbt wird

> Erhebung 11.09.2026. Kein eigener ID-Raum: Die Anforderungen stehen in
> `podcast.md` (POD). Hier steht, **womit** sie gebaut werden.

Ein früheres Hörspiel-Projekt desselben Autors produziert seit Monaten Alben in
der „Tiefenschnitt"-Struktur (Intro, vier Inhalts-Tracks, Outro), bisher
**einstimmig**. Fast alles, was TeachBuddys Podcast braucht, liegt dort
fertig.

## Was direkt trägt

### Mehrstimmigkeit — gebaut, aber nie benutzt
`album_builder.py` erkennt Sprecher-Präfixe und löst sie über eine
Voice-Map auf (dort als T1621 geführt):

```python
_PREFIX_RE = re.compile(r"^([A-ZÄÖÜ][A-ZÄÖÜ ]*?):\s*", re.UNICODE)
# "MODERATOR: Wie misst man das?"  →  voices["MODERATOR"]
```

Damit ist POD-1 (Moderator und Gast) eine Konfigurationsfrage, kein Umbau:
Der Skript-Agent schreibt Sprecherzeilen mit Präfix, die Voice-Map ordnet zu.

**Das ist der größte Einzelfund.** Die Mehrstimmigkeit war für den
Hörspiel-Vorbild vorbereitet und blieb dort ungenutzt; der Podcast ist ihr
erster echter Anwendungsfall.

### Vertonung
`tts/azure.py` — Azure OpenAI, Schnittstelle `synthese(text=, voice=) → mp3`.
Schmal genug, um sie unverändert zu übernehmen.

Eigene Zugangsdaten nach E-11a, damit Kosten trennbar bleiben und ein Limit
im einen Projekt das andere nicht stilllegt.

### Zusammenfügen mit Pausen
`_synthese_bundle_mit_pausen` vertont **je Absatz einzeln** und fügt Stille
dazwischen, `_concat_chunks_mit_pausen` erledigt alles in einem
ffmpeg-Aufruf.

Eine Erfahrung aus dem Code, die man sonst teuer selbst macht:

> Re-encode mit libmp3lame bei jedem Concat-Schritt — sonst DTS-Müll.

Pausen sind konfigurierbar: 0,55 s zwischen Absätzen, 1,8 s nach dem Titel.
Das erfüllt POD-9.

### Nicht neu bauen
- **Caching über Hash-Index** (`.index.json`): Ein Track wird nur neu
  vertont, wenn sich Titel, Text, Stimme **oder die Voice-Map** geändert
  haben. Spart bei jeder Korrektur an einer Lektion den Rest der Folge.
- **Bündelung** nach Wortzahl (Schwelle 450) und Dauerabschätzung über
  2,5 Wörter je Sekunde. Genau genug, um POD-3 (5 bis 10 Minuten) zu
  steuern.

## Was TeachBuddy zusätzlich braucht

### 1. Marker entfernen vor der Vertonung
Das Skript trägt Beleg-Marker je Sprecherzeile (AUF-8a). Sie werden vor der
Vertonung entfernt (AUF-8c), sonst liest die Sprachausgabe „B 17" mitten im
Satz vor.

Der Hörspiel-Vorbild kennt das Problem nicht — dort gibt es keine Belege.
**Das ist der einzige Punkt, an dem der geerbte Pfad wirklich erweitert
werden muss.**

### 2. Zeitmarken statt Tracks
Das Hörspiel liefert getrennte Track-Dateien. Der Podcast liefert **eine**
Datei plus Zeitmarken für den Abspieler (`kapitelmarken` im Datenvertrag der
Entwurf).

Die Dauern fallen beim Bauen ohnehin an; sie müssen nur kumuliert und
mitgeschrieben werden statt verworfen.

### 3. Zeichenzahl mitschreiben
POD-7a verlangt, die vertonte Zeichenzahl je Folge festzuhalten. Der
Hörspiel-Vorbild tut das nicht.

### 4. Überlaufprobe entfällt, Längenprobe kommt
Statt der Grafik-Überlaufprobe (E-19c) braucht der Podcast eine Längenprobe:
Liegt die fertige Folge zwischen 5 und 10 Minuten? Sonst neu schneiden.

## Was nicht geerbt wird

Die **Album-Struktur** (Intro, vier Inhalts-Tracks, Outro) ist für
Kinderhörspiele gedacht. Eine Lektion ist eine Folge, kein Album.

Die **Shared Assets** (vorproduzierte Intros und Outros je Stimme) sind
sinnvoll und später übernehmbar, aber nichts für V1.

## Entschieden am 11.09.2026

**Stimmen:** `MODERATOR → shimmer`, `GAST → onyx`. Tauschbar nach einer
Hörprobe, dann aber für den ganzen Lernpfad (POD-7b).

**Belege im Audio:** keine. Die Marker werden vor der Vertonung entfernt
(AUF-8c), der Hörer darf voraussetzen, dass alles belegt ist. Nachschlagen
geht über die Folie oder über den Lernpartner (POD-5a).
