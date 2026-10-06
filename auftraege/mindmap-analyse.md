# Auftrag: Strukturanalyse für die Mindmap eines Kapitels

Rolle: **Struktur** — also Claude (AUF-16).

## Warum es diesen Schritt gibt

Die Mindmap hat bis zum 11.09.2026 die `titel` der Wissenseinheiten als
Knotenbeschriftung genommen. Ein `titel` ist nach dem Mikropublikations-Modell
eine **Behauptung**, also ein ganzer Satz:

> „Welche von zwei Antworten ein Judge vorzieht, hängt auch davon ab, in
> welcher Reihenfolge sie ihm vorliegen"

Zehn solcher Sätze in Kästen sind keine Mindmap, sondern eine Stichpunktliste
mit Kurven dazwischen. Das verstößt gegen **MMP-3** („Ein Knoten trägt ein
Stichwort, keinen Satz") und kostet die Grafik ihre Sprache.

E-19a verlangt vor jeder Grafik eine Strukturanalyse. Sie hat für Folien
gegolten und muss auch hier gelten (11.09.2026). Dieser Auftrag ist
dieser Schritt.

## Was **nicht** entsteht

**Keine Bilddatei und keine fertige SVG.** MMP-8 und E-19b halten fest: Die
Mindmap ist eine Ansicht auf den Begriffsgraphen, kein Artefakt. Sie muss
mitwachsen, wenn sich eine Einheit ändert (BIB-20), Lernstand je Knoten
zeigen (MMP-7) und in die Lektion führen (MMP-2). Ein gerendertes Bild kann
davon nichts.

Es entstehen **Daten**: Stichworte und Achsen. Gezeichnet wird daraus im
Browser.

## Was entsteht

### 1. Je Wissenseinheit ein `stichwort`

In den Kopf jeder `WE-*.md` im Kapitel kommt eine neue Zeile, direkt unter
`titel`:

```yaml
stichwort: Position Bias
```

Regeln:

- **Zwei bis vier Wörter.** Was länger ist, ist wieder ein Satz.
- **Der Gegenstand, nicht die Aussage.** WE-0001 behauptet etwas *über*
  Position Bias; ihr Stichwort ist `Position Bias`.
- **Eindeutig im Kapitel.** Zwei Knoten mit demselben Stichwort sind für den
  Lesenden derselbe Knoten. Tritt das auf, unterscheide fachlich korrekt
  (`Position Bias` / `Position Bias messen`), nicht durch Nummerierung.
- **Fachbegriff vor Umschreibung.** Steht in der Einheit ein etablierter Term,
  ist er das Stichwort. Nichts erfinden, was im Text nicht vorkommt.
- Sonst nichts an der Datei ändern. Kein Inhalt, keine Belege, keine
  Reihenfolge.

### 2. Je Kapitel eine Analyse

Neue Datei `mindmap/<Kapitel>.md` neben `einheiten/` und `lektionen/`:

```markdown
---
kapitel: F
kern: LLM-as-a-Judge
achsen:
  - id: A1
    frage: Welche Verzerrungen gibt es?
    einheiten: [WE-0001, WE-0004, WE-0006]
  - id: A2
    frage: Was hilft dagegen?
    einheiten: [WE-0003, WE-0007]
erzeugt: 2026-09-11
---

## Kernaussage
<ein Satz: worum es in diesem Kapitel geht>

## Beziehungen
<Welche Art von Ordnung ist das — Hierarchie, Ablauf, Ursache und Wirkung,
Vergleich, Teil und Ganzes? Ein Absatz, begründet.>

## Layout
<Warum diese Achsen und diese Reihenfolge. Ein Absatz.>

## Verworfen
<Welche Gliederung du erwogen und aus welchem Grund verworfen hast. Ohne
diesen Abschnitt ist die Analyse nicht prüfbar.>
```

Regeln für die Achsen:

- **Zwei bis vier Achsen.** Eine ist keine Gliederung, fünf sind keine
  Übersicht.
- **Die Achse ist eine Frage**, kein Substantiv. Der Entwurf hat das
  vorgemacht: „Wer urteilt?", „Welche Form hat das Urteil?". Eine Frage sagt,
  wonach sortiert wurde; ein Substantiv lässt es offen.
- **Jede Einheit hängt an genau einer Achse.** Gehört eine an zwei, ist die
  Gliederung falsch gewählt — dann wähle eine andere, statt doppelt zu
  hängen. Querbezüge zeigt die Ansicht ohnehin separat (MMP-5).
- **Keine Einheit fällt weg.** Die Vereinigung aller `einheiten` ist genau
  die Menge der Wissenseinheiten des Kapitels.
- **`kern` ist selbst ein Stichwort**, zwei bis vier Wörter.

## Womit du arbeitest

Die Wissenseinheiten des Kapitels. Welche das sind, steht in den Lektionen
des Kapitels unter `wissenseinheiten:`.

**Du liest den Inhalt, nicht nur die Titel.** Das Stichwort für eine Einheit
steckt im Text, nicht in der Überschrift.

## Woran der Auftrag scheitert

- Ein Stichwort mit mehr als vier Wörtern.
- Eine Einheit ohne Achse oder an zwei Achsen.
- Eine Achse, die keine Frage ist.
- Ein fehlender Abschnitt „Verworfen".
