# Oberfläche — Spec     (ID-Präfix: OBF)

> Status: Entwurf · Vorgaben 10.09.2026 · folgt APP-1..11, BIB-26

## Problem

Ein Lernpfad hat schnell fünfzehn Kapitel mit je fünf bis zehn Lektionen. Das
sind hundert anklickbare Dinge. Die Übersichtsseite ist deshalb nicht die
Beiwerk-Seite, sondern die schwierigste des ganzen Systems: Sie muss viel
zeigen und trotzdem ruhig bleiben.

Zweitens: Beim Lernen unterwegs zählt, **wo man stehengeblieben ist**. Eine
Liste ohne Fortschritt zwingt den Nutzer, sich das selbst zu merken.

## 1. Übersicht und Navigation

### OBF-1 — Ausklappende Hierarchie
Die Übersicht zeigt Lernpfad, Kapitel und Lektionen als aufklappbare
Struktur. Geschlossen zeigt sie nur Kapitel.

Hundert Lektionen auf einmal sind keine Übersicht. Zugeklappt sind es
fünfzehn Zeilen, und das ist eine.

### OBF-2 — Eine Lektion ist von der Übersicht aus einen Griff entfernt
Ein Tippen auf eine Lektion öffnet sie in der Lektionsansicht, in der der
Abspieler liegt. Es braucht keine Zwischenseite und keine zweite Auswahl.

**Die Übersicht spielt selbst nichts ab** (11.09.2026). Der Abspieler
trägt inzwischen das Bild der Einheit, die Kapitelmarken, das Tempo, die
Sekundensprünge, den Offline-Schalter und den Zustand. Das passt nicht in eine
Listenzeile, und ein halber Abspieler an zwei Orten ist schlechter als ein
ganzer an einem.

### OBF-2a — Drei Ebenen, und jede hat ihren Ort
Die App hat drei Navigationsebenen: **Übersicht**, **Kapitel**, **Lektion**.

- Die **Übersicht** zeigt den Lernpfad. Sie navigiert und bedient nicht.
- Die **Kapitelansicht** trägt, was zum ganzen Kapitel gehört: Mindmap
  (OBF-12), Sprachgespräch (OBF-13) und die Lektionen des Kapitels.
- Die **Lektionsansicht** trägt Abspieler, Bild, Folie und Fragen.

Aus der Übersicht führt **ein** Griff ins Kapitel und **ein** Griff in die
Lektion. Mehrere Knöpfe auf dasselbe Ziel gibt es nicht.

Die Kapitelansicht war vorher nirgends beschrieben, obwohl OBF-12 und OBF-13
„je Kapitel" verlangen. Ohne sie hätte das Kapitel Inhalte, aber keinen Ort.

### OBF-3 — Der Zustand ist am Symbol ablesbar
Jede Lektion trägt sichtbar einen von vier Zuständen: **ungehört**,
**angefangen**, **gehört**, **Fragen beantwortet**.

„Gehört" und „Fragen beantwortet" sind getrennt, weil sie verschiedene Dinge
bedeuten. Wer nur hört, hat konsumiert; wer die Fragen beantwortet hat, hat
sich geprüft.

### OBF-4 — Ein Kapitel zeigt seinen Fortschritt zusammengefasst
Am Kapitel steht, wie viel davon gehört ist, ohne dass man es aufklappen muss.

Das ist die Frage, die man beim Öffnen der App zuerst hat: Wo bin ich stehen
geblieben, und was fehlt noch.

### OBF-5 — Weiterhören ohne Suchen
Die Übersicht bietet die zuletzt angefangene Lektion an prominenter Stelle an.

### OBF-6 — Symbole tragen Bedeutung, nicht Dekoration
Jedes Symbol in der Übersicht steht für einen Zustand oder eine Art von
Inhalt (Lektion, Mindmap, Diskussion, Fragen). Es gibt keine Symbole, die
nur schmücken.

### OBF-7 — Der Fortschritt liegt auf dem Server
Der Lernstand wird auf dem Server gespeichert, nicht nur im Browser.

Sonst ist er weg, sobald der Browser aufräumt, und auf dem Laptop weiß die
App nicht, was auf dem Telefon gehört wurde.

## 2. Die Lektion

### OBF-8 — Hören und Folie nebeneinander
Eine Lektion zeigt den Abspieler und ihre Übersichtsfolie zusammen. Die Folie
ist nicht hinter einem zweiten Klick versteckt.

### OBF-9 — Die Folie ist strukturiert und grafisch
Je Lektion gibt es genau eine Folie mit den wichtigsten Punkten und den
zentralen Abbildungen. Sie ist zum Anschauen gemacht, nicht zum Lesen eines
Fließtexts (POD-13).

### OBF-9a — Jede Abbildung lässt sich groß ansehen und zoomen
Wo eine Abbildung steht — das Bild einer Lektion, die Mindmap eines Kapitels —
öffnet ein Tippen sie formatfüllend. Dort lässt sie sich zoomen und
verschieben, mit Rad, zwei Fingern oder Tastatur.

Eine Übersichtsfolie in Kartengröße auf einem Telefon ist nicht lesbar. Was
als Code entsteht (Mindmap, E-19), bleibt bei jedem Zoomschritt scharf: es wird
neu gezeichnet, nicht hochgerechnet. Das gemalte Bild einer Lektion (E-19d)
wird hochgerechnet; seine 1536 Pixel Breite reichen dafür auf dem Telefon.

### OBF-10 — Belege sind auf der Folie erreichbar
Jede Kernaussage der Folie führt zu ihrem Beleg (POD-14).

Im Audio kann der Lernende nichts nachschlagen, hier schon. Das ist die
Stelle, an der TB-1 für ihn sichtbar wird.

### OBF-10a — Abspieltempo einstellbar
Der Abspieler bietet mindestens 1×, 1,25×, 1,5× und 2×. Die Einstellung gilt
über Lektionen hinweg, statt bei jeder Folge zurückzuspringen.

Wer sich in ein Thema eingehört hat, hört schneller. Wer eine schwierige
Stelle nachvollzieht, geht zurück auf 1×. Beides muss ohne Umweg gehen.

### OBF-10b — Vor- und Zurückspringen in Sekundensprüngen
Vorwärts und rückwärts in festen Sprüngen (etwa 15 Sekunden), zusätzlich zu
den Kapitelmarken.

Beim Hören unterwegs ist „das habe ich nicht mitbekommen" der häufigste
Bedienwunsch, und dafür ist eine Zeitleiste zu grob.

### OBF-11 — Drei bis vier Fragen je Lektion
Jede Lektion hat einen Fragenblock mit drei bis vier Wiederholungsfragen, in
der App beantwortbar (PRF-6, PRF-7).

Kurz genug, dass man ihn direkt nach dem Hören macht. Ein Block mit fünfzehn
Fragen wird verschoben und dann nie gemacht.

## 3. Das Kapitel

### OBF-12 — Mindmap je Kapitel
Jedes Kapitel hat eine Mindmap, die sich öffnen, zoomen und verschieben
lässt (MMP-4).

### OBF-13 — Diskussionspartner je Kapitel, gesprochen
Zu jedem Kapitel lässt sich ein **Sprachgespräch** starten. Nicht je Lektion.

Eine einzelne Lektion trägt kein Gespräch; erst im Kapitel gibt es genug
Zusammenhang, um zu widersprechen und zu vertiefen.

### OBF-13a — Echtzeit, nicht Wartezeit
Das Gespräch läuft über die Realtime-Schnittstelle mit direkter
Audioverbindung (E-20, E-20a). Antwortzeiten liegen im Bereich eines
natürlichen Gesprächs, nicht im Bereich eines Auftrags.

Unterbrechen muss möglich sein. Ein Partner, den man nicht unterbrechen kann,
hält Vorträge.

### OBF-13b — Die Kosten laufen sichtbar mit
Während einer Sprachsitzung zeigt die App die laufende Dauer **und die
laufenden Kosten**. Am Ende steht beides in der Bilanz (DIS-22).

Entschieden in `decisions/E-21.md`: Es gibt **keine** Obergrenze, an der
abgebrochen wird. Damit ist die Sichtbarkeit die einzige Kontrolle, und
deshalb Pflichtfunktion statt Zugabe.

### OBF-13c — Nach 15 Sekunden Stille schließt sich die Sitzung
Ohne Sprache schließt sie sich selbst; Wiederaufnehmen ist ein Griff, der
Verlauf bleibt.

Fünfzehn Sekunden sind lang genug zum Nachdenken und kurz genug, dass ein
weggelegtes Telefon nicht minutenlang weiterläuft. Abgefangen wird nicht der
nachdenkende, sondern der abgelenkte Lernende — dort entstehen die Kosten,
an die niemand denkt.

### OBF-13d — Eine eigene Ansicht für die Kosten
Heute, dieser Monat, und je Lernpfad. Die letzte Zahl beantwortet, ob sich ein
weiterer Lernpfad lohnt (E-21d).

Alle Zahlen sind **gemessen**, nicht hochgerechnet (E-21b).

## 4. Der Diskussionspartner

### OBF-14 — Er kennt sein Kapitel vollständig
Der Diskussionspartner bekommt die Wissenseinheiten des Kapitels samt Belegen
als Kontext, nicht eine Auswahl davon.

Ein Kapitel liegt weit unter der Grenze, ab der sich Abruf-Maschinerie lohnt
(E-9). Alles mitzugeben ist hier nicht der Notbehelf, sondern der bessere Weg:
Es gibt kein Retrieval, das etwas übersehen könnte.

### OBF-15 — Er eröffnet, statt zu warten
Er hat Einstiegsfragen zum Kapitel parat und stellt eine davon, statt eine
leere Eingabezeile anzubieten.

### OBF-16 — Er fragt zurück
Er prüft im Gespräch, ob der Lernende verstanden hat, statt nur zu antworten.
Eine Rückfrage an der richtigen Stelle ist mehr wert als eine weitere
Erklärung.

### OBF-17 — Belegt und Unbelegtes sind unterscheidbar
Antworten aus den Wissenseinheiten des Kapitels tragen ihren Beleg (DIS-7).
Was der Diskussionspartner darüber hinaus beisteuert, ist im Gespräch
sichtbar als **nicht aus der Bibliothek** gekennzeichnet.

Das ist die Bedingung, unter der freies Weiterrecherchieren im Gespräch
zulässig ist. Ohne die Kennzeichnung wäre der Diskussionspartner der bequeme
Seitenausgang aus TB-1: Er beantwortet dieselben Fragen unbelegt und
schneller, und danach nimmt niemand mehr den belegten Weg.

### OBF-18 — Aus Unbelegtem wird ein Rechercheauftrag
Was im Gespräch unbelegt beigesteuert wurde, lässt sich mit einem Griff als
Rechercheauftrag aufnehmen (DIS-9).

Damit wird der Seitenausgang zum Rückkanal: Die Lücken zeigt der Lernende,
nicht der Kurator.

### OBF-19 — Bewertet wird die Folge, an einer Stelle
Eine Lektion trägt **einen** Knopf für eine Rückmeldung, und zwar in der
Werkzeugzeile neben „offline sichern", „als gehört markieren" und „zu den
Fragen" — dort, wo die übrigen Handgriffe an der Folge schon liegen. Er öffnet
ein Blatt mit einer Art (`gut`, `unklar`, `zu lang`, `falsch`, `anderes`) und
optional einem Satz.

**Die Fassung der Pipeline wird mitgeschrieben** (AUF-18a), und zwar auf dem
Server, nicht vom Browser mitgeschickt. Eine Bewertung gilt für den Stand, der
gehört wurde; wer sie später gegen die dann aktuelle Fassung liest, deutet sie
falsch.

Rückmeldungen liegen in `lernstand.db`, nicht im Index: Der Index wird aus
Dateien gebaut und ist wegwerfbar (BIB-18b), eine Rückmeldung nicht.

> **Der erste Bau hatte ein Symbol je Wissenseinheit** — es war so
> gefordert („gib mir bei jeder Einheit ein kleines Symbol"). Nachdem es
> dastand, hat er es verworfen: **„ich will den podcast bewerten und nicht
> 100.000 text stellen."**
>
> Er hat recht, und die Lehre ist allgemeiner als dieser Knopf: Der Lernende
> **hört** eine Folge. Danach hat er ein Urteil über die Folge, nicht über
> ihren dritten Absatz. Ein Knopf je Kernaussage verlangt, dass er beim Hören
> mitliest und je Absatz entscheidet; bei 309 Einheiten ist das Arbeit ohne
> Ertrag. Die Granularität der Rückmeldung folgt der Granularität des
> Erlebens, nicht der der Datenhaltung.
>
> Der Datenweg trägt weiter eine Einheit (`einheit_id` ist nullable). Die
> Oberfläche fragt nicht danach.

**Der Anlass ist ein Verlust.** POD-16 und E-25 sind beide aus mündlichem
Feedback im Chat entstanden, und ein Teil davon ist dabei untergegangen: Der
Wunsch nach Beispielen und Anekdoten war schon einmal gesagt worden, wurde
nicht aufgeschrieben und tauchte erst am 13.09.2026 wieder auf — als POD-19.
Ein Knopf an der Folge ist der kürzere Weg als ein Satz im Chat.

### OBF-19a — Die Folie sagt, was in der Folge steckt
Am Fuß der Übersichtsfolie stehen Fassung und Tag der Erzeugung, aufklappbar
zu der Liste dessen, was diese Fassung besser macht (AUF-18a).

Ist die Folge nicht auf dem jetzigen Stand, sagt die Zeile das — **sie drängt
aber nicht zum Neubau.** POD-16a gilt: Gutes Vorhandenes wird nicht entwertet,
nur weil es neuere Regeln gibt.
