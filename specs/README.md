# Specs

`specs/` ist die **Quelle der Wahrheit** für das Soll-Verhalten von
TeachBuddy — **lebende Specs**: Sie beschreiben, wie das System sich *heute*
verhalten soll, nicht was wann geändert wurde.

## Die eine Regel

> **Verhalten ändern = Spec im selben PR ändern.**

## Aufbau

- `constitution.md` — übergeordnete Prinzipien (TB-*), selten geändert.
- `bibliothek.md` (BIB) — die Wissensschicht.
- `aufbereitung.md` (AUF) — das Agenten-Modell und der Format-Vertrag.
- `formate/<name>.md` — je Lernformat eine Spec mit eigenem ID-Präfix.
- `app.md` (APP) — Auslieferung und PWA.

Gegliedert wird nach **Verhalten**, nicht nach Code-Modulen.

## Eine Anforderung schreiben

Jede Anforderung hat eine **stabile ID** (Präfix + laufende Nummer) und einen
testbaren Satz, am besten im Wenn/Dann-Stil:

```markdown
### BIB-3 — Abrufdatum festhalten
Wenn das System eine Webquelle aufnimmt, speichert es das Datum des Abrufs
zusammen mit der URL.
```

IDs werden **nie** neu vergeben und nie umnummeriert. Ein Ticket nennt die
IDs, die es umsetzt — das ist der Link zwischen Ticket, Spec und Code.

## Offene Punkte

Eine Anforderung, die noch nicht entschieden ist, trägt statt eines
Verhaltenssatzes eine Zeile

```markdown
> **OFFEN (E-4):** <die Frage in einem Satz>
```

und verweist auf den Eintrag in `../decisions/offen.md`. So steht die Lücke
dort, wo sie hingehört, statt in einer Sammelliste zu verschwinden.

**Eine Spec mit vielen OFFEN-Markern ist ehrlich, keine mit erratenen
Antworten.** Ein OFFEN wird aufgelöst, indem die Entscheidung fällt und in
`decisions/` begründet wird — nicht, indem jemand eine plausible Antwort
hineinschreibt.
