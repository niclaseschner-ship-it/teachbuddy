# Prüfer — Spec     (ID-Präfix: PRF)

> Status: Entwurf · folgt AUF-2, AUF-11..AUF-14

## Problem

Zu wissen, dass man etwas verstanden hat, ist etwas anderes, als es zu
glauben. Der Prüfer erzeugt aus dem Material Fragen und bewertet die
Antworten, damit die Lücke sichtbar wird, bevor sie in einer echten Prüfung
sichtbar wird.

## 1. Fragen

### PRF-1 — Fragen entstehen aus Belegen
Jede Frage geht auf mindestens einen Beleg zurück, und die Musterantwort
steht in der Bibliothek.

Eine Frage, deren Antwort nirgends steht, ist keine Prüfungsfrage, sondern
ein Ratespiel.

### PRF-2 — Mehrere Fragearten
Das System erzeugt Wissensfragen (Was gilt?), Verständnisfragen (Warum?) und
Anwendungsfragen (Was folgt daraus im Fall X?).

Wer nur Wissensfragen stellt, prüft das Gedächtnis und nicht das Verstehen.

### PRF-3 — Schwierigkeit folgt der Einheit
Die Schwierigkeit einer Frage richtet sich nach dem Grad der Wissenseinheit
(BIB-13).

### PRF-4 — Musterantwort mit Belegverweis
Jede Frage trägt eine Musterantwort und die Belege, auf denen sie steht.

### PRF-5 — Fragen sind ein Vorrat
Erzeugte Fragen werden gespeichert und wiederverwendet, statt bei jeder
Prüfung neu erzeugt zu werden (TB-4).

## 2. Prüfen

### PRF-6 — Freie Antwort
Der Lernende antwortet in eigenen Worten. Multiple Choice ist nicht der
Standardfall.

Ankreuzen prüft Wiedererkennen. Formulieren prüft Verstehen, und es ist die
Form, in der auch die echte Prüfung stattfindet.

### PRF-7 — Bewertung mit Begründung
Das System bewertet die Antwort und begründet die Bewertung am Beleg, statt
nur richtig oder falsch zu melden.

### PRF-8 — Teilrichtig ist ein eigenes Ergebnis
Eine Antwort kann teilweise richtig sein. Das System benennt, was getroffen
war und was fehlte.

### PRF-9 — Die ehrliche Enthaltung
Wenn das System nicht sicher entscheiden kann, ob eine Antwort trägt, sagt
es das, statt zu raten (TB-8).

Eine falsch als richtig bewertete Antwort ist der teuerste Fehler in diesem
Format: Der Lernende hakt das Thema ab.

### PRF-10 — Nachfragen erlaubt
Der Lernende kann zu einer Bewertung nachfragen, und das System antwortet
belegt (wie DIS-7).

## 3. Verlauf

### PRF-11 — Ergebnisse werden festgehalten
Das System speichert je Frage, wann sie gestellt und wie sie bewertet wurde.

### PRF-12 — Schwaches wird wiedergeholt
Fragen, die schlecht beantwortet wurden, kommen in späteren Prüfungen
bevorzugt wieder.

> **OFFEN (E-14):** Ob daraus ein richtiges Wiederholungsverfahren mit
> wachsenden Abständen wird. Das ist wirksam, aber es ist ein eigenes
> Stück Arbeit und braucht Nutzung über Wochen, bevor es sich lohnt.
> Vorschlag: erst die einfache Bevorzugung, das Verfahren später, wenn
> Daten da sind (TB-9).

### PRF-13 — Lücken zeigen auf Einheiten
Das System sagt nicht nur, welche Fragen schwach beantwortet wurden, sondern
welche Wissenseinheiten dahinterstehen, damit der Lernende weiß, wohin er
zurück muss.
