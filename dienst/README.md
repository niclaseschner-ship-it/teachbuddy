# dienst/ — der Flask-Dienst nach Datenvertrag v2

Ein Dienst, sparsam (APP-10). Er liest aus dem Index und schreibt in den
Lernstand — zwei Dateien, zwei Sorten Wahrheit:

| | |
|---|---|
| `arbeit/index.db` | gebaut aus der Bibliothek, **wegwerfbar**, nur lesend (BIB-18b) |
| `arbeit/lernstand.db` | eigene Wahrheit, wird geschrieben, überlebt jeden Indexbau (OBF-7) |

Beide liegen unter `arbeit/` (siehe `pfade.py`).

## Starten

```bash
python -m bibliothek.index          # erst den Index bauen (Bibliothek -> arbeit/index.db)
python -m dienst.app                # 127.0.0.1:5088
```

Vorgaben lassen sich über die Umgebung setzen: `TEACHBUDDY_INDEX`,
`TEACHBUDDY_LERNSTAND`, `TEACHBUDDY_HOST`, `TEACHBUDDY_PORT`. Der Port 5088 ist
gewählt.

## Die Endpunkte

| | |
|---|---|
| `GET /api/lernpfad/<id>` | Kapitel und Lektionen |
| `GET /api/lektion/<id>` | Detail **mit ausgeschriebenen Belegen** |
| `GET /api/kapitel/<id>/mindmap` | Knotenbaum |
| `GET /api/beleg/<id>` | ein Beleg samt Fundstelle und Quelle |
| `PUT /api/lektion/<id>/fortschritt` | `{ position_sek, fragen }` |
| `POST /api/fortschritt/nachtrag` | Liste; Konflikt: späterer Zeitpunkt gewinnt |
| `PUT /api/einstellungen` | `{ tempo }` |
| `POST /api/frage/<id>/antwort` | `{ text }` |

Dazu **ein Endpunkt außerhalb des Vertrags**: `GET /api/zustand` meldet, wann
der Index gebaut wurde, was er enthält und welche Befunde offen sind. Er steht
hier, weil ein Dienst, der nicht sagen kann, ob sein Index veraltet ist, nicht
zu betreiben ist — und weil diese Lieferung ihre Lücken zeigen soll, statt sie
zu verstecken.

Fehler haben immer dieselbe Form: `{ "fehler": "<code>", "grund": "<satz>" }`,
mit 400 bei falscher Eingabe und 404 bei Unbekanntem.

## R-5 — Belege reisen mit

Der wichtigste Punkt. Belege kommen **ausgeschrieben** in derselben Antwort,
nicht als nachzuladende IDs:

```json
{ "folie_punkte": [ { "text": "…", "belege": ["B-0002-01"], "art": "belegt",
                      "wissenseinheit": "WE-0001" } ],
  "einheiten": [ { "id": "WE-0001", "stichwort": "Position Bias",
                   "titel": "…die Kernaussage als ein Satz…",
                   "kurzfassung": "…", "grad": "einstieg",
                   "belege": ["B-0002-01"] } ],
  "belege": { "B-0002-01": { "aussage": "…", "zitat": "…", "stelle": "…",
                             "quelle_id": "Q-0002", "zuversicht": "hoch" } } }
```

`einheiten` traegt den **Kopf** je Wissenseinheit und ist seit dem 13.09.2026
dabei: Die Uebersichtsfolie gliedert sich danach (POD-13a) und zeigt
`stichwort` und `titel`, waehrend die Absaetze aus `folie_punkte` darunter
wegklappen. Nichts davon wird erzeugt — es stand schon in der Bibliothek und
wurde nur nicht herausgegeben. `folie_punkte` bleibt unveraendert die Wahrheit
des Inhalts; jeder Punkt nennt in `wissenseinheit`, wohin er gehoert.

Im Zug ist der Server nicht erreichbar. Ein Beleg, der dann fehlt, ist genau der
Zustand, den TB-1 ausschließt — die Folie sagte dann „das ist belegt", ohne es
zeigen zu können. Für die Mindmap gilt dasselbe.

Eine unbekannte Beleg-ID wird nicht verschwiegen, sondern kommt als
`{"fehlt": true}` mit — die Oberfläche kann „Beleg fehlt" zeigen, statt
„belegt" zu behaupten.

`GET /api/beleg/<id>` bleibt zusätzlich bestehen, für Belege aus einem
Gespräch, das ohnehin Verbindung braucht.

## Was der Dienst nicht tut

**Er bewertet keine Antworten.** `POST /api/frage/<id>/antwort` gibt
`nicht_bewertbar` mit Begründung zurück. Die Bewertung braucht ein Modell
(PRF-7), das über die Abo-CLIs läuft (TB-5) und hier nicht angeschlossen ist.
PRF-9 verlangt in diesem Fall die Enthaltung: Eine falsch als richtig bewertete
Antwort ist der teuerste Fehler des Formats, weil der Lernende das Thema
abhakt. Die Antwort wird trotzdem gespeichert — sie geht nicht verloren.

**Er erfindet keine Lektionen.** Die Bibliothek hat keine Lektionsschicht
(BIB-26/27 sehen sie vor, die Dateien gibt es nicht). Betroffene Antworten
tragen ein `_fehlt` mit Begründung.

**Er stellt die Bibliothek nicht als Ganzes bereit** (APP-8a). Er liefert
Lektionen, Folien, Fragen und den Fortschritt aus, sonst nichts.

## Die drei Dateien

| | |
|---|---|
| `app.py` | die Endpunkte |
| `lernstand.py` | `lernstand.db` — Fortschritt, Einstellungen, Antworten |
| `folie.py` | Folienpunkte aus dem Inhalt einer Wissenseinheit ablesen (R-6, BIB-11) |

`folie.py` erfindet nichts: Das Material markiert jede Aussage mit ihren Belegen
(`[B-0002-01]`) und jede Einordnung mit `[E]` — genau die Unterscheidung, die
BIB-11 verlangt und der Vertrag als `art` führt. Was es nicht gibt, ist ein
Merkmal für `strittig`; es wird deshalb nicht gesetzt.

## Tests

```bash
python3 -m pytest dienst/tests
```

Die Tests laufen gegen das echte Material in `demo/`. Kein
Ersatz-Fixture-Repo: Ein erfundenes Material würde genau die Abweichungen
glattbügeln, um derentwillen es die Tests gibt.

pytest legt seine temporären Verzeichnisse unter `arbeit/pytest` an,
nicht unter `/tmp` — gesetzt in `tests/conftest.py`, damit keine `pytest.ini`
im Wurzelverzeichnis dem Nachbarn in `podcast/` die Sammelpfade vorschreibt.
