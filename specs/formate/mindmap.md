# Mindmap — Spec     (ID-Präfix: MMP)

> Status: Entwurf · folgt AUF-2, AUF-11..AUF-14

## Problem

Podcast, Diskussion und Prüfer sind linear oder punktuell. Was fehlt, ist der
**Blick von oben**: Wie hängt das alles zusammen, was ist Haupt-, was
Nebenstrang, und wo stehe ich gerade.

Die Mindmap ist deshalb zweierlei: Zusammenfassung eines Bereichs und
Landkarte über den ganzen Lernpfad.

## 1. Aufbau

### MMP-1 — Struktur kommt aus der Bibliothek
Die Gliederung folgt den Wissenseinheiten und ihren Voraussetzungen (BIB-12),
nicht einer frei erfundenen Ordnung.

Die Beziehungen stehen bereits in der Bibliothek. Sie dort abzulesen statt
neu zu erfinden, hält Mindmap und Lernpfad automatisch synchron.

### MMP-2 — Knoten führt zur Einheit
Jeder Knoten verweist auf die Wissenseinheit, aus der er stammt.

### MMP-3 — Beschriftungen sind kurz
Ein Knoten trägt ein Stichwort, keinen Satz.

Das Stichwort steht als `stichwort` im Kopf der Wissenseinheit, zwei bis vier
Wörter. Es wird nicht beim Zeichnen aus dem Titel gekürzt, sondern in der
Strukturanalyse gesetzt (MMP-10). Der `titel` einer Einheit ist eine
Behauptung und damit ein ganzer Satz; er gehört nicht in den Knoten.

Die Behauptung bleibt am Knoten als `satz` und erscheint beim Antippen
zusammen mit Kurzfassung und Belegen (MMP-6).

### MMP-10 — Vor der Mindmap steht die Strukturanalyse
Ein Kapitel bekommt seine Gliederung nicht beim Zeichnen, sondern aus einer
Analyse, die vorher läuft (E-19a, E-24). Sie liegt als Datei in der
Bibliothek und nennt:

- `kern` — das Stichwort der Wurzel,
- `achsen` — Gliederungsachsen, jede **eine Frage** („Wer urteilt?"), nicht
  ein Substantiv. Wie viele, sagt MMP-10a,
- je Achse die Wissenseinheiten, die unter ihr hängen.

**Jede Einheit hängt an genau einer Achse.** Gehört eine an zwei, ist die
Gliederung falsch gewählt; Querbezüge zeigt MMP-5 ohnehin getrennt. Keine
Einheit fällt weg.

### MMP-10a — Zwei Ebenen, und keine mehr
Die Zahl der Achsen richtet sich nach dem Kapitel, nicht nach einer festen
Vorgabe. Es gilt eine **Obergrenze an Breite**: Kein Knoten trägt mehr als
neun Kinder, und eine Unterachse bleibt unter sieben Knoten. Darüber liest man
keine Karte mehr, sondern eine Liste.

Reicht eine Ebene dafür nicht, gliedert die Analyse in **zwei**: Achsen mit
`unterachsen`. Die Wissenseinheiten hängen immer an der **untersten** Achse;
MMP-10 („jede Einheit an genau einer Achse") gilt dort.

**Mehr als zwei Ebenen nicht.** Eine Achse unter einer Achse unter einer Achse
ist keine Gliederung mehr, sondern ein Inhaltsverzeichnis.

Stand heute: K-02 trägt drei Achsen auf einer Ebene, K-01 und K-04 je neun mit
Unterachsen, K-03 acht, K-05 sechs.

> Bis zum 13.09.2026 stand hier „zwei bis vier Achsen". Das war für ein
> Kapitel mit einer Lektion richtig und für K-01 mit dreizehn nicht mehr: Die
> Analyse hat zwei Ebenen geliefert, `bibliothek/lesen.py` hat die obere
> **weggeworfen** und die untere zur ersten gemacht — mit dem Kommentar, der
> Renderer könne nur eine Ebene. Das Ergebnis waren **39 gleichrangige Fragen
> an einer Wurzel**, also genau die Stichpunktliste mit Kurven dazwischen,
> gegen die E-24 geschrieben wurde.
>
> Der Renderer zeichnet `kinder` rekursiv und konnte es längst. Nur diese eine
> Stelle hat die Struktur nicht weitergegeben. Die Analysen mussten dafür
> nicht neu laufen — sie waren die ganze Zeit richtig.

Die Analyse trägt einen Abschnitt **Verworfen**. Ohne ihn sieht man, was
gewählt wurde, aber nicht, wogegen — und kann die Gliederung nicht prüfen.

Fehlt die Analyse, hängen die Knoten nach ihren Voraussetzungen nebeneinander,
und die Ansicht sagt das. Eine geratene Gliederung wäre schlimmer als keine.

### MMP-4 — Zwei Zoomstufen
Es gibt die Mindmap über einen Bereich und die über den ganzen Lernpfad.
Die Lernpfad-Ansicht zeigt Bereiche als Knoten, ohne deren Innenleben.

Eine Mindmap mit 200 Knoten ist keine Übersicht mehr.

### MMP-5 — Querbezüge sind sichtbar
Wo eine Wissenseinheit auf eine Einheit in einem anderen Bereich verweist,
zeigt die Mindmap das als Verbindung.

## 2. Als Zusammenfassung

### MMP-6 — Kernaussage je Knoten
Ein Knoten lässt sich aufklappen und zeigt dann die Kurzfassung der
Wissenseinheit samt Belegen.

Damit ist die Mindmap zugleich das Nachschlagewerk und nicht nur ein Bild.

### MMP-7 — Lernstand ist ablesbar
Wo Prüferergebnisse vorliegen (PRF-11), zeigt die Mindmap je Knoten den
Stand an.

Das ist die Stelle, an der die Landkarte ihren größten Nutzen entfaltet: Man
sieht auf einen Blick, wo es dünn ist.

## 3. Form

### MMP-8 — Textformat als Wahrheit
Die Mindmap liegt als Textformat vor, nicht als Bild.

Ein Bild lässt sich nicht durchsuchen, nicht versionieren und nicht
aktualisieren, wenn sich eine Einheit ändert (BIB-20).

> **OFFEN (E-15):** Welches Format. Markmap (Markdown-Listen, im Browser
> gerendert) ist der billigste Weg und passt zur Ablage aus BIB-18.
> Alternativen wären Mermaid oder ein eigenes JSON. Empfehlung: Markmap,
> solange keine Anforderung dagegen spricht.

### MMP-9 — In der App bedienbar
Die Mindmap ist in der PWA auf- und zuklappbar und auf dem Telefon
brauchbar.

> **OFFEN (E-16):** Eine große Mindmap auf einem Telefondisplay ist ein
> ungelöstes Bedienproblem. Möglicherweise ist auf kleinen Bildschirmen eine
> ausklappbare Liste die bessere Darstellung derselben Daten. Das lässt
> sich erst am Prototyp entscheiden.

### MMP-11 — Eine Mindmap je Kapitel, über alle seine Lektionen
Die Mindmap gehört dem **Kapitel**, nicht der Lektion (BIB-26). Sie zeigt alle
Wissenseinheiten aller Lektionen des Kapitels.

Das ist ihr Zweck: Sie ist die Landkarte des Themas. Eine Mindmap je Abschnitt
wäre die Landkarte eines Ausschnitts, und dreizehn davon ergeben keine
Übersicht.

Solange nicht alle Lektionen gebaut sind, zeigt die Mindmap, was es gibt, und
**sagt, wie viel das ist**. Eine Karte, die einen Ausschnitt für das Ganze
ausgibt, ist schlimmer als eine, die ihre Grenze nennt (TB-8).
