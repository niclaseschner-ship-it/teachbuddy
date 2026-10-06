# bibliothek/ — Dateien lesen, Index bauen, Index fragen

Die Wahrheit liegt in der Bibliothek — `demo/` oder deiner eigenen (`TEACHBUDDY_WISSEN`, angelegt mit `python -m bibliothek.anlegen`) —
als Markdown mit YAML-Frontmatter (BIB-18, [`decisions/E-9.md`](../decisions/E-9.md)).
Hier steht nur das Werkzeug, das daraus eine **wegwerfbare** SQLite-Datei macht
(BIB-18b) und darauf beantwortet, was Dateien schlecht können.

Dieses Verzeichnis schreibt **nie** in die Bibliothek.

## Die drei Dateien

| | |
|---|---|
| `lesen.py` | parst Quellen, Quellenversionen, Fundstellen, Belege, Wissenseinheiten, Lernpfade |
| `index.py` | baut `index.db` — Tabellen, typisierte `kanten`, drei FTS5-Tabellen |
| `abfragen.py` | Rückwärtskanten, Volltextsuche, Belegauflösung, BIB-20 |

Dazu `yaml_min.py`: ein YAML-Leser für genau die Teilmenge, die im Frontmatter
vorkommt. Die Randbedingung ist „Flask, sonst Standardbibliothek"; PyYAML wäre
eine Abhängigkeit für vier Formen. Der Leser ist **streng** — was er nicht
kennt, wirft er, statt zu raten.

## Index bauen

```bash
python -m bibliothek.index                                  # Vorgaben
python -m bibliothek.index --wissen pfad/zur/bibliothek \
                           --ziel pfad/zum/index.db
```

Der Index wird **immer komplett neu gebaut**, nie inkrementell. Gebaut wird in
`index.db.neu` und am Ende per `os.replace` an den Platz geschoben: Ein
abgebrochener Bau lässt den alten Index stehen, statt einen halben zu
hinterlassen.

`index.db` liegt nicht im Git (`.gitignore`) und wird **nie von Hand geändert**.
Ist er kaputt, wird er weggeworfen.

Ohne Angaben liest er `TEACHBUDDY_WISSEN` (sonst `demo/`) und schreibt nach
`arbeit/index.db` (siehe `pfade.py`).

## Was im Index steht

```
quellen · versionen · fundstellen · belege · einheiten · pfade · abschnitte
lektionen · lektion_einheiten      ← die Schicht aus BIB-26/27, heute leer
kanten                             ← typisiert (BIB-22), mit Gültigkeit (BIB-23)
befunde                            ← wo Material und Spec auseinandergehen
meta                               ← wann gebaut, aus welcher Wurzel, Zählungen
fts_aussagen · fts_zitate · fts_einheiten
```

### Die Kanten

Eine Kante trägt `von`, `typ`, `nach`, dazu `gilt_ab`, `gilt_bis`, `zuversicht`,
`gesetzt_von` und `erklaert_in` (die Datei, in deren Frontmatter sie steht).

Die Spalte `bib22` sagt, ob der Typ im Vokabular aus BIB-22 steht. Der
Evidenzgraph braucht drei Typen, die dort fehlen (`hat_fassung`, `enthaelt`,
`entnommen_aus`), und das Material führt ein viertes (`siehe_auch`). Sie werden
gebaut und **markiert**, nicht auf einen BIB-22-Typ umgedeutet.

```
Q --hat_fassung--> V --enthaelt--> F <--entnommen_aus-- B --stuetzt--> WE
                                                        WE --setzt_voraus--> WE
                                                        WE --widerspricht--> WE
                                                        WE --siehe_auch-----> WE
```

### Die Befunde

`befunde` ist die Liste der Stellen, an denen das echte Material von
`specs/bibliothek.md` abweicht. Sie entsteht beim Lesen, landet im Index und
ist über `GET /api/zustand` abrufbar.

`schwere: fehler` heißt: eine Datei war nicht lesbar oder ein Verweis zeigt ins
Leere. Davon gibt es heute keinen. `schwere: abweichung` heißt: Spec und
Material sagen Verschiedenes — das ist erwartet und dokumentiert.

## Fragen stellen

```python
from bibliothek.index import oeffne
from bibliothek import abfragen

db = oeffne("dienst/arbeit/index.db")

abfragen.rueckwaerts(db, "WE-0001", "stuetzt")      # wer belegt diese Einheit?
abfragen.suche(db, "Position Bias")                  # BM25 über drei FTS-Tabellen
abfragen.beleg(db, "B-0002-01")                      # Beleg → Fundstelle → Quelle
abfragen.belege_ausgeschrieben(db, ["B-0002-01"])    # die Kurzform für R-5
abfragen.veraltet_durch(db, "Q-0002")                # BIB-20
abfragen.begriffsbaum(db, ["WE-0001", "WE-0002"])    # Knotenbaum für die Mindmap
```

`veraltet_durch` nimmt eine Quelle, eine Quellenversion, eine Fundstelle, einen
Beleg oder eine Wissenseinheit und läuft die Evidenzkette abwärts. Solange es
keine Lektionsschicht gibt, ist `artefakte` leer — und die Antwort sagt das mit
`_fehlt`, statt leer auszusehen.

## Tests

`python3 -m pytest dienst/tests` (vom Repo-Wurzelverzeichnis). Die Tests liegen
bei ihrem Verbraucher; sie laufen gegen das echte Material, und fehlt
`demo/`, werden sie übersprungen.
