# Podcast mit Handreichung — Spec     (ID-Präfix: POD)

> Status: Entwurf · folgt AUF-2, AUF-11..AUF-14

## Problem

Wissen im Ohr, während man geht, kocht oder fährt. Der Podcast ist das
Format für die erste Begegnung mit einem Thema: Er trägt den Bogen, nicht
die Details. Die **Handreichung** fängt auf, was das Ohr nicht behält, und
ist das, was man vor der Prüfung noch einmal überfliegt.

Beides gehört zusammen und wird in einem Auftrag erzeugt: Wer die
Handreichung getrennt schreibt, bekommt zwei Fassungen desselben Themas, die
sich unterscheiden.

## 1. Die Folge

### POD-1 — Moderator und Gast
Eine Folge ist ein Gespräch zwischen genau zwei Rollen: einem **Moderator**,
der durch das Thema führt und nachfragt, und einem **Gast**, der die Sache
erklärt.

Ein Monolog aus der Sprachausgabe ermüdet nach wenigen Minuten. Der Moderator
bringt außerdem die Fragen unter, die der Lernende selbst hätte, ohne dass der
Text sie behaupten muss.

### POD-1a — Die Rollen sind ungleich verteilt
Der Gast trägt den Inhalt, der Moderator die Struktur. Das Verhältnis der
Sprechanteile ist deutlich zugunsten des Gastes.

Zwei gleich viel erklärende Stimmen sind kein Gespräch, sondern ein
aufgeteilter Vortrag, und der Hörer verliert die Orientierung, wem er zuhört.

### POD-1b — Der Moderator eröffnet und schließt
Der Moderator nennt am Anfang das Thema und fasst am Ende zusammen (POD-4).

### POD-2 — Der Moderator fragt nur Belegtes
Die Fragen des Moderators beziehen sich auf die übergebenen Wissenseinheiten.
Er darf zuspitzen und um Beispiele bitten, aber keine Sachfrage stellen,
deren Antwort nicht in der Bibliothek steht.

Sonst bricht AUF-3 an der Stelle, an der es am wenigsten auffällt: in der
Antwort auf eine erfundene Frage.

### POD-3 — Eine Lektion dauert 5 bis 10 Minuten
Eine Folge entspricht genau einer Lektion (BIB-26) und liegt zwischen fünf
und zehn Minuten. Reicht das Material nicht, wird mit der nächsten Lektion
zusammengelegt; ist es zu viel, wird geteilt.

Die Zeitspanne ist der Zuschnitt, nicht die Zahl der Wissenseinheiten. Wer
nach Einheiten schneidet, bekommt Folgen von zwei und von zwanzig Minuten,
und beides ist zum Hören unterwegs unbrauchbar.

### POD-4 — Gliederung ist hörbar
Eine Folge beginnt mit einem Überblick über das, was kommt, und endet mit
einer Zusammenfassung.

### POD-5 — Im Audio wird nicht belegt
Im gesprochenen Text stehen **keine** Quellenangaben und keine Beleg-Marker.
Eine Quelle wird nur genannt, wenn sie zum Verständnis gehört — etwa bei
einer Norm oder einem namentlichen Standpunkt, über den gestritten wird.

Vorgelesene Fußnoten sind unhörbar, und sie sind unnötig: **Der Hörer darf
voraussetzen, dass alles belegt ist.** Genau dafür gibt es die Bibliothek.

### POD-5a — Die drei Orte des Belegs
Derselbe Beleg ist an drei Stellen verschieden präsent, und das ist Absicht:

| Ort | Beleg |
|---|---|
| **Audio** | abwesend — man kann beim Hören ohnehin nichts nachschlagen |
| **Übersichtsfolie** | sichtbar je Kernaussage, aufklappbar (POD-14, OBF-10) |
| **Gesprächspartner** | auf Nachfrage, mit Zitat und Fundstelle (DIS-7) |

Wer beim Hören zweifelt, fragt hinterher den Lernpartner. Das ist der
angenehmere Weg als eine vorgelesene Fußnote und zugleich der Grund, warum
der Partner `bibliothek_nachschlagen` hat (DIS-26).

**Die Voraussetzung dafür ist AUF-8a**: Weil jede Sprecherzeile im Skript
ihren Marker trägt und die Belegprobe sie prüft, *darf* das Audio ohne
Belegapparat auskommen. Die Prüfung ist passiert, sie wird nur nicht
vorgetragen.

## 2. Vertonung

### POD-6 — Sprachsynthese über Azure
Die Vertonung läuft über die Azure-OpenAI-Sprachausgabe, hinter der
Provider-Schnittstelle aus TB-7. Ein früheres Hörspiel-Projekt hat diesen Weg
bereits gebaut, einschließlich einer
Sprecher→Voice-Map für Mehrstimmigkeit.

Lokale Synthese über Piper ist verworfen: klanglich trägt sie eine
20-Minuten-Folge nicht (TB-5).

### POD-7 — Je Rolle eine Stimme
Moderator und Gast bekommen unterschiedliche Stimmen über eine
Sprecher→Voice-Map (entschieden 11.09.2026):

```
MODERATOR → shimmer      führt, fragt, fasst zusammen
GAST      → onyx         erklärt, trägt den Inhalt
```

Technisch geerbt aus dem Hörspiel-Vorbild: Der Skript-Agent
schreibt Sprecherzeilen mit Präfix (`MODERATOR: …`), die Map löst sie auf.
Damit ist Mehrstimmigkeit Konfiguration, kein Umbau.

Die Zuordnung folgt der Konvention, dass die fragende Stimme heller und die
erklärende tiefer liegt. **Tauschbar nach einer Hörprobe**, aber dann für den
ganzen Lernpfad (POD-7b).

### POD-7b — Die Zuordnung ist fest
Eine Rolle behält ihre Stimme über alle Folgen eines Lernpfads.

Wechselnde Stimmen zwingen den Hörer, sich in jeder Folge neu zu sortieren.

### POD-7a — Vertonung kostet Geld je Zeichen
Anders als beim übrigen System entstehen hier laufende Kosten pro erzeugter
Folge. Das System hält je Folge die vertonte Zeichenzahl fest.

Ohne diese Zahl lässt sich nicht beantworten, was ein Lernpfad kostet, und
genau diese Frage wird nach dem ersten vollen Pfad kommen. Sie mitzuschreiben
kostet nichts, sie nachträglich zu rekonstruieren ist unmöglich.

### POD-8 — Segmente werden zusammengefügt
Das System vertont je Sprecherwechsel ein Segment und fügt die Segmente mit
ffmpeg zu einer Datei zusammen.

### POD-9 — Pausen an den Fugen
Zwischen zwei Segmenten liegt eine hörbare Pause.

### POD-10 — Audio überlebt die App
Die fertige Folge liegt als gewöhnliche Audiodatei auf der Platte und ist
ohne TeachBuddy abspielbar.

### POD-10a — Sinnabschnitt ist die Sprecherzeile
Für die Belegprobe (AUF-8a) gilt beim Podcast jede Sprecherzeile als
Sinnabschnitt. Die Marker stehen im Skript und werden vor der Vertonung
entfernt (AUF-8c).

### POD-11 — Skript bleibt erhalten
Das System speichert das Sprechskript neben dem Audio.

Ohne Skript ist eine Folge nach einer Bibliothekskorrektur nur komplett neu
erzeugbar, und ein Fehler im Text ist nicht auffindbar, ohne 20 Minuten zu
hören.

## 3. Handreichung

### POD-12 — Handreichung folgt der Folge
Die Handreichung ist nach denselben Abschnitten gegliedert wie das Audio und
nennt zu jedem Abschnitt die Zeitmarke.

### POD-13 — Dichte statt Prosa
Die Handreichung ist eine Stichwortunterlage in der Art von
Vorlesungsfolien: Kernaussagen, Begriffe, Zahlen, Abbildungen wo nötig.
Sie wiederholt nicht den gesprochenen Text in Absätzen.

### POD-13a — Die Kernaussage ist der Titel der Wissenseinheit
Die Folie gliedert sich **nach Wissenseinheiten**, nicht nach Absätzen und
nicht nach Kapitelmarken. Je Einheit steht sichtbar:

| Was | Woher | Umfang |
|---|---|---|
| Marke | `stichwort` der Einheit (E-24) | zwei bis vier Wörter |
| Kernaussage | `titel` der Einheit | ein Satz |
| Nachweis | die Belege der Einheit | Pillen, öffnen das Zitat |

Die **Prosa der Einheit klappt darunter weg** („mehr lesen"), zusammen mit
der Kurzfassung.

Die Folie wurde zweimal als zu viel Text gemeldet, am 11.09. und am
13.09.2026: „aktuell ist es eine ganze Textwand … ich will knappen
strukturierten Text, übersichtlich die wichtigsten Inhalte der Folge, zum
Ausklappen Nachweise und mehr wenn gewünscht."

**Der erste Versuch hat an der falschen Schicht gearbeitet.** Er hat die
Punkte nach Kapitelmarken gruppiert. Das half nicht, weil jeder einzelne
Punkt ein Absatz ist: `folie_punkte` sind die Absätze des Einheiten-Inhalts,
also der Volltext. Gemessen an L-H3 waren das 15 Punkte mit im Mittel 38
Wörtern, zusammen 593 Wörter. Sortierte Prosa ist immer noch Prosa.

**Erzeugt wird dafür nichts.** Der Kopf einer Einheit war längst modelliert
und wurde nur nicht herausgegeben. Damit erfüllt die Folie POD-13 ohne einen
weiteren Agentenlauf und ohne eine zweite Fassung desselben Themas, die
auseinanderlaufen könnte.

Gemessen nach dem Umbau, dieselbe Lektion: **156 Wörter sichtbar statt 929**
— 17 %. Der Rest ist einen Klick entfernt.

### POD-14 — Jede Kernaussage mit Belegverweis
Jede Kernaussage der Handreichung trägt den Verweis auf ihren Beleg.

Die Handreichung ist damit die Stelle, an der TB-1 für den Lernenden
sichtbar wird. Im Audio kann er nichts nachschlagen, hier schon.

### POD-15 — Druckbar
Die Handreichung lässt sich als PDF ausgeben.

> **OFFEN (E-12):** Ob PDF vom Server erzeugt wird oder die App die Druckansicht
> des Browsers nutzt. Das Zweite ist deutlich weniger Code.

### POD-16 — Jede Folge rechnet ihre Theorie an einem Fall durch
Eine Folge führt Begriffe ein und **wendet sie danach auf einen benannten,
wirklichen Fall an**. Nicht als Beispielsatz nebenbei, sondern als eigener
Abschnitt: Man nimmt einen konkreten Gegenstand und geht mit dem eben
eingeführten Vokabular durch ihn hindurch.

Rückmeldung nach dem ersten Hören des Evaluations-Kapitels, 12.09.2026:

> „Stark, gute Theorie, aber schwer fassbar. Interessant wäre, wenn wir die
> Theorie ganz konkret an einem Beispiel einordnen. Zum Beispiel bei den
> Benchmarks mal einem erklären mit dem eingeführten Fachvokabular."

Das ist kein Wunsch nach Auflockerung. Eine Taxonomie, die man nicht an etwas
anlegen kann, bleibt Vokabeln lernen. Der Fall ist die Probe darauf, ob die
Begriffe tragen — und er deckt auf, wo sie es nicht tun.

**Der Fall muss wirklich sein und benannt.** SWE-bench, nicht „ein Benchmark".
Was über ihn gesagt wird, ist belegpflichtig wie alles andere (TB-1).

**Die Zuordnung ist eine Einordnung** (AUF-13). Dass SWE-bench' Aufgabenstellung
die *Anfrage* ist und das Repository die *Umgebung*, steht in keiner Quelle;
das ist unsere Ordnung, die wir anlegen. Sie wird als solche gekennzeichnet
und nicht als Befund ausgegeben.

**Kein neues Vokabular im Fall.** Er wendet an, was die Folge eingeführt hat.
Wer dort neue Begriffe braucht, hat sie vorher vergessen.

Derselbe Fall darf über mehrere Folgen eines Kapitels wiederkehren. Das ist
sogar die stärkere Form: Derselbe Benchmark, jedes Mal mit mehr Vokabular
betrachtet, zeigt den Zuwachs unmittelbar.

**Gerade die Stellen, an denen das Vokabular nicht greift, gehören dazu.** Ein
Fall, bei dem alles glatt aufgeht, ist eine Werbebroschüre für die Taxonomie.
Wo die Zuordnung hakt, lernt man, wo die Begriffe enden.

### POD-16a — Nicht rückwirkend
Fertige Folgen werden dafür **nicht** neu gebaut. Rückmeldung vom 12.09.2026: „Ich will
auch nicht eine Einheit zweimal anhören müssen."

Eine Regel, die gutes Vorhandenes entwertet, kostet mehr als sie bringt: Der
Lernende hört die Folge dann nicht besser, sondern noch einmal. Die Regel
gilt für alles, was noch nicht gebaut ist.

## 4. Sprache

> Aus E-25, nach der zweiten Hörrunde am 13.09.2026: „Die Sprache ist immer
> noch sperrig und klingt nicht natürlich … ich will ja kein Buch vorgelesen
> bekommen." Die Messwerte, auf denen dieser Abschnitt steht, stehen in
> `decisions/E-25-entwurf.md`.

An der Satzlänge liegt es nicht — die war schon kurz (Median elf Wörter über
47 Folgen). Der Buchklang kam aus vier anderen Quellen, und jede hat hier
ihre Regel.

### POD-17 — Die beiden Rollen sind Personen, keine Funktionen
POD-1 beschreibt Moderator und Gast über ihre **Aufgabe**. Das genügt nicht:
Beide sprachen daraufhin dasselbe Deutsch, nur in verschiedener Länge.

**Der Moderator ist der informierte Laie.** Er kennt das Feld, aber nicht
dieses Thema. Er darf zugeben, dass er etwas noch nicht hat. Sein tragender
Zug ist, den eben eingeführten Begriff **in eigenen, einfachen Worten
nachzusagen** und sich bestätigen oder korrigieren zu lassen.

**Der Gast ist die Praktikerin, die es gebaut hat.** Sie spricht aus
Erfahrung und sagt „ich": wo sie es falsch gemacht hat, was sie überrascht
hat, was sie heute anders macht. Sie sagt „das weiß ich nicht", wo sie es
nicht weiß.

Diese Aufteilung ist nicht Geschmack, sondern Mechanik: Sie macht das
Vereinfachen zur **Aufgabe des Moderators** statt zu einer Stilbitte an den
Gast, die zwei Absätze später vergessen ist. Und sie erzeugt die zweite
Ebene als Gespräch, nicht als angehängten Erklärsatz.

### POD-17a — Jeder Fachbegriff wird einmal übersetzt, nicht ersetzt
Beim ersten Auftreten steht der Begriff **in seiner genauen Form**, und kurz
darauf einmal in Alltagswörtern.

Ausdrücklich: „Klar, das Fachvokabular bleibt formell, muss es auch." Die
einfache Fassung steht **daneben**, nie an seiner Stelle. Ein Auftrag, der das
nur halb liest, verwässert die Terminologie — und dann greifen Handreichung,
Prüfer und die nächste Folge nicht mehr ineinander.

Geht die Übersetzung über den Beleg hinaus, trägt sie `[E]`.

### POD-17b — Gesprochenes Deutsch statt Nominalstil
Handelnde Personen statt Vorgangsnomen, Aktiv statt Passiv. „Wer prüft was?"
statt „die Prüfung von". Kein zusammengesetztes Substantiv, das man im
Sprechen nicht durchhält.

Gemessen: 1404 Wortformen auf `-ung`/`-heit`/`-keit` bei nur 192 persönlichen
Pronomen auf 42.330 Wörter. Es wurde bewertet, gemessen und verlangt, aber
niemand tat etwas.

### POD-17c — Keine Bestätigungsformel am Zeilenanfang
„Genau", „Ja", „Richtig" als Auftakt sind zu vermeiden. Wer zustimmt, zeigt es
am Inhalt.

51 % aller Gast-Zeilen begannen so. Das ist kein Charakter, sondern ein Reflex,
und er macht jede Zeile zur Bestätigung der vorigen.

### POD-17d — Eine Frage trägt ein Fragezeichen
Betrifft nicht den Stil, sondern die Satzmelodie: Die Sprachausgabe liest
einen Fragesatz ohne Fragezeichen mit fallender Stimme, also wie einen
vorgetragenen Satz. Nur 28 % der Moderator-Zeilen hatten eines.

### POD-18 — Die Folge spricht nie über ihre eigene Herstellung
Im gesprochenen Text kommen **Material, Auftrag, Wissenseinheiten, Belege,
Marker und Quellenlage nicht vor**. Der Hörer kennt diese Begriffe nicht, und
sie gehen ihn nichts an.

Das ist keine Stilfrage, sondern ein Fehler, der beim Testhören am 13.09.2026 aufgefallen ist:
Der Moderator sagte in einer fertigen Folge, er habe keine Beispiele in den
Daten. In 18 von 47 gebauten Folgen steht ein ganzer **gesprochener** Abschnitt
„Wenn das Material nicht trägt", in dem die beiden über ihre Arbeitsanweisung
reden — „Der Auftrag verlangt einen durchgerechneten wirklichen Fall. Trägt das
Material dafür?"

**Ursache war die Anweisung selbst** (`auftrag.md`): Sie hieß „sag das im
Abschnitt ‚Wenn das Material nicht trägt'", und Abschnitte sind im Skript
`## `-Überschriften, die dem Hörer als Kapitelmarke angezeigt und deren Inhalt
vertont wird. Die Anweisung war so zu lesen, wie sie befolgt wurde.

**Was stattdessen gilt:**

* Trägt das Material die ganze Folge nicht, wird sie **abgelehnt** — die
  Ablehnung ist ein Rückgabewert an die Pipeline, kein Gesprächsgegenstand.
* Trägt es einen einzelnen Teil nicht, etwa den Fall aus POD-16, dann
  **entfällt dieser Teil wortlos**. Eine Lücke wird nicht besprochen.
* **Davon unberührt bleibt POD-5 und die Ehrlichkeit über die Sache selbst.**
  „Dazu gibt es bisher kaum belastbare Zahlen" ist eine Aussage über den
  Forschungsstand und gehört hinein. „Das steht nicht in unserem Material" ist
  eine Aussage über uns und gehört nicht hinein. Der Unterschied ist, worüber
  der Satz redet.

### POD-19 — Ein Bild oder eine kleine Geschichte je Folge
Zusätzlich zum durchgerechneten Fall (POD-16) trägt jede Folge **mindestens
eine Stelle, an der die Sache anschaulich wird**: ein Vergleich, ein Bild, eine
kurze Geschichte aus der Praxis des Gastes, eine Zahl, die man weitererzählt.

Das war früher schon angemerkt worden, und es ist damals nicht aufgeschrieben
worden — POD-16 hat nur den durchgerechneten Fall festgehalten. Das ist nicht
dasselbe: Der Fall ist die **Probe**, ob die Begriffe tragen. Das Bild ist der
**Haken**, an dem sie hängen bleiben.

**Erfunden wird dabei nichts.** Der Stoff dafür steht meist schon im Material
und wird nur nicht gehoben — „tausend gleiche Anfragen, achtzig verschiedene
Antworten" ist bereits eine Geschichte. Ein Vergleich, der über den Beleg
hinausgeht, ist eine Einordnung und trägt `[E]`. Eine erfundene Anekdote aus
dem Leben des Gastes wäre eine Erfindung und verstößt gegen TB-1.
