# Offene Entscheidungen

Stand 13.09.2026. Entschieden bisher: E-1, E-2, E-3, E-5, E-6, E-9, E-10, E-11, E-15, E-19, E-20, E-21, E-24, E-25 (siehe `E-*.md`). Reihenfolge ist die empfohlene Bearbeitungsreihenfolge:
Was oben steht, blockiert Arbeit weiter unten.

## Blockierend für den ersten Prototyp

### E-4 — Streaming der Chat-Antwort
Schrittweise oder als Block?
*Betrifft: APP-13*

## Bibliothek

### E-7 — Skala für den Schwierigkeitsgrad
Drei Stufen genügen vermutlich.
*Betrifft: BIB-13*

### E-8 — Einzelfreigabe oder Vertrauensstufen für Quellen
Einzelfreigabe ist der ehrliche Start und wird ab dem zweiten Lernpfad zur
Bremse.
*Betrifft: BIB-16*

## Formate

### E-11a — Eigener Azure-Zugang
Entschieden: TeachBuddy liest nur `TEACHBUDDY_AZURE_OPENAI_*`. TeachBuddy sollte
eigene Schlüsselnamen bekommen, damit die Kosten trennbar bleiben und ein
Limit im einen Projekt das andere nicht stilllegt.
*Betrifft: POD-6, TB-7*

### E-12 — PDF der Handreichung: Server oder Browserdruck
*Betrifft: POD-15*

### E-13 — Diskussionsrunde als Text oder vertont
**Empfehlung: Text zuerst.**
*Betrifft: diskussion.md, Abschnitt 4*

### E-14 — Wiederholungsverfahren mit wachsenden Abständen
**Recherchiert, entscheidungsreif:** Der Stand der Technik ist **FSRS**
(Free Spaced Repetition Scheduler), Open Source, an über 500 Millionen echten
Lernvorgängen gemessen. Es braucht 20 bis 30 % weniger Wiederholungen als das
alte SM-2 bei gleicher Behaltensrate und ist selbst ohne persönliche
Anpassung für 99,5 % der Nutzer treffsicherer. Seit Anki 23.10 dort eingebaut.

Kein Grund, etwas Eigenes zu bauen. Offen ist nur, **wann** wir es einziehen:
Es braucht Nutzung über Wochen, bevor es etwas bringt.
*Betrifft: PRF-12*

### E-15 — entschieden am 11.09.2026: eigener Knotenbaum, kein Markmap
Markmap rendert Markdown-Listen. Das trägt nicht, sobald ein Knoten
Wissenseinheit, Belege, Lernstand, Strittig-Marke und einen Lektionssprung
tragen muss — das ist Struktur, die sich in einer Einrückung nicht ausdrücken
lässt.

Die Mindmap ist stattdessen eine **Projektion des Begriffsgraphen** (BIB-21)
als Knotenbaum mit Feldern, gerendert als SVG. Form steht im Datenvertrag der
Entwurf unter `_mindmap_beispiel`.
*Betrifft: MMP-8, E-19b*

### E-16 — Mindmap auf dem Telefon
Erst am Prototyp entscheidbar.
*Betrifft: MMP-9*

### E-17 — Offline-Bewertung im Prüfer
Musterantwort sofort zum Selbstvergleich, echte Bewertung nachgereicht?
*Betrifft: APP-7*

## Material

### E-18 — Woher gutes Kursmaterial kommt
Entschieden ist: **Web-Recherche** ist die Quellenart, mit der begonnen wird
(BIB-14a, über die Abo-CLI). Offen ist die Stufe darüber.

Frei zugängliche Webquellen sind für Überblickswissen brauchbar und für
Prüfungsstoff oft zu dünn: verstreut, unterschiedlich tief, ohne Gewähr für
Vollständigkeit. Wo ein Lernpfad einer Prüfungsordnung folgen soll, führt
vermutlich kein Weg an bezahltem Material vorbei, sei es ein Kurs, ein
Fachbuch oder ein Normzugang.

Zu klären, sobald das Pilotthema feststeht:
- Welche Art Material trägt das Thema wirklich?
- Wenn ein Kurs registriert wird: Kommt das Material als PDF heraus, das
  TeachBuddy aufnehmen kann, oder nur als Videostrom hinter einem Login?
  Das Erste ist eine Quelle, das Zweite ist keine.
- Ab dann braucht es die Quellenart „eigene Datei" (Ordner, den TeachBuddy
  liest), die heute noch nicht vorgesehen ist.

**Diese Frage bestimmt die Qualität des ganzen Systems.** TeachBuddy kann
nicht besser sein als seine Bibliothek, und die Bibliothek nicht besser als
ihre Quellen. Der Prototyp kann mit Webquellen laufen; ein echter Lernpfad
vermutlich nicht.

## Noch offen

- **Womit fangen wir inhaltlich an?** Die Bibliothek braucht ein erstes
  echtes Thema, sonst bleibt der Prototyp eine Attrappe. Blockiert den
  Durchstich.

## Aus den App-Vorgaben vom 10.09.2026

### E-22 — Curricula als Gliederungsquelle
**Ansatz (11.09.2026):** Statt die Gliederung selbst zu erfinden und
Quellen einzeln zu suchen, an **Curricula renommierter Universitäten**
orientieren. Bisher kamen die Quellen von AWS und Microsoft, weil die Suche
von verfügbaren Schulungen ausging; neutral ist besser.

**Der Befund des ersten Durchstichs stützt das.** Zwei Dinge gingen schief,
und beide löst ein Syllabus:

1. Die selbst gebaute Gliederung trug nicht (vier von acht Begriffen nicht
   belegbar, drei Achsen als Taxonomie ausgegeben).
2. Die Quellen waren anbieterlastig, weil die Suche dort ansetzte.

Ein Syllabus liefert **beides**: eine erprobte Reihenfolge samt
Voraussetzungen, und eine kuratierte Leseliste mit Primärquellen. Ein
Hochschullehrer hat diese Arbeit bereits gemacht und seinen Namen daruntergesetzt.

Zu klären: wie das als Rolle in die Pipeline kommt, welche Kurse taugen,
und was bei Themen ohne Hochschulkurs passiert.
*Betrifft: BIB-14, BIB-28, E-18*
