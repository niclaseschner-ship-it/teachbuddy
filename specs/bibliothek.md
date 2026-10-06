# Bibliothek — Spec     (ID-Präfix: BIB)

> Status: Entwurf · trägt TB-1, TB-2

## Problem

Wissen zu einem Thema liegt verstreut: in Fachartikeln, Normen, Kursunterlagen,
Blogbeiträgen, PDFs im eigenen Archiv. Wer daraus lernen will, hat zwei
schlechte Optionen: alles selbst lesen, oder ein Sprachmodell fragen und
hoffen, dass es stimmt.

Die Bibliothek ist der dritte Weg. Sie sammelt das Material **einmal**, prüft
es, und hält fest, woher jeder Satz stammt. Alles, was TeachBuddy später
ausspielt, wird aus ihr gespeist und ist damit nachschlagbar.

## Die vier Dinge, aus denen sie besteht

Die Begriffe sind bewusst wenige. Jeder hat genau eine Aufgabe.

| Begriff | Was es ist | Beispiel |
|---|---|---|
| **Quelle** | ein Herkunftsort mit Metadaten | „ISO 27001:2022" |
| **Quellenversion** | die Fassung, die zu einem Zeitpunkt vorlag | Abruf vom 10.09.2026 |
| **Fundstelle** | eine Stelle in einer Quellenversion, wörtlich | Abschnitt 5.2 b), Zitat |
| **Beleg** | die aus einer Fundstelle abgeleitete Aussage | „Die Leitlinie muss dokumentiert sein" |
| **Wissenseinheit** | ein lernbarer Baustein aus mehreren Belegen | „Was eine Leitlinie leisten muss" |
| **Lernpfad** | eine geordnete Folge von Wissenseinheiten | „ISMS-Grundlagen in 8 Einheiten" |

Ein Format (Podcast, Prüfer, …) arbeitet **immer auf Wissenseinheiten**, nie
direkt auf Quellen. Das ist die Trennlinie aus TB-2.

**Fundstelle und Beleg sind getrennt, weil sie verschiedenen Dingen gehören.**
Die Fundstelle gehört der Quelle: Dort steht dieser Wortlaut. Der Beleg ist
die Deutung: Das folgt daraus. Wer beides in ein Feld legt, kann später einen
Deutungsfehler nicht mehr von einem Zitierfehler unterscheiden.

Dieselbe Trennung findet sich im Micropublications-Modell aus der
Publikationsforschung, wo eine Kette `Aussage → stützt sich auf → Fundstelle
mit Zitat → steht in → Quelle` bis zum Original zurückverfolgbar bleibt.

## 1. Quellen aufnehmen

### BIB-1 — Quelle mit Herkunft
Das System speichert zu jeder Quelle mindestens: Titel, Urheber, Art
(Web, PDF, Buch, Norm, Video, Gespräch), Fundort (URL oder Dateipfad),
Veröffentlichungsdatum soweit ermittelbar, und eine stabile Quellen-ID.

### BIB-2 — Fehlende Metadaten sind sichtbar
Wenn ein Metadatum nicht ermittelbar ist, speichert das System es als
ausdrücklich unbekannt und nicht als leeren Wert. Ein unbekanntes
Veröffentlichungsdatum ist eine Information, kein fehlendes Feld.

### BIB-3 — Abrufdatum festhalten
Wenn das System eine Webquelle aufnimmt, speichert es das Datum des Abrufs
zusammen mit der URL.

### BIB-4 — Wortlaut sichern
Das System legt zu jeder Quelle den zum Abrufzeitpunkt verwendeten Wortlaut
ab (Volltext bei Web, Datei bei PDF).

Der Grund: Webseiten ändern sich. Ohne gesicherten Wortlaut zeigt ein Beleg
nach einem halben Jahr auf etwas, das dort nicht mehr steht.

### BIB-4a — Die Quellenversion ist ein eigenes Ding
Ein gesicherter Wortlaut ist eine **Quellenversion** mit eigener ID. Ändert
sich eine Quelle, entsteht eine zweite Version neben der ersten; die alte
wird nicht überschrieben.

Fundstellen zeigen auf eine Quellenversion, nicht auf die Quelle. Nur so
zeigt ein zwei Jahre alter Beleg weiterhin auf genau die Fassung, aus der er
gewonnen wurde, auch wenn die Quelle inzwischen etwas anderes sagt.

### BIB-5 — Lizenz und Nutzbarkeit
Das System hält je Quelle fest, unter welchen Bedingungen ihr Inhalt
verwendet werden darf, soweit erkennbar.

Entschieden in `decisions/E-6.md`: **nur Vermerk**, keine Durchsetzung,
solange der Nutzerkreis eine Person ist. Die Entscheidung ist neu zu treffen,
bevor ein Artefakt das Haus verlässt.

### BIB-6 — Dublettenerkennung
Wenn eine Quelle aufgenommen wird, die inhaltlich bereits vorliegt, meldet
das System das und legt keine zweite an.

## 2. Belege

### BIB-7 — Beleg zeigt auf eine Fundstelle
Ein Beleg verweist auf eine Fundstelle in einer Quellenversion (Abschnitt,
Seite, Zeitmarke), nicht auf die Quelle als Ganzes. Ein Beleg ohne Fundstelle
ist unvollständig.

### BIB-8 — Aussage getrennt vom Zitat
Das System speichert je Beleg beides getrennt: den wörtlichen Ausschnitt der
Quelle und die daraus abgeleitete Aussage in eigenen Worten.

Der Grund: Nur so lässt sich später prüfen, ob die Ableitung trägt. Wer nur
die Paraphrase speichert, kann einen Interpretationsfehler nicht mehr finden.

### BIB-9 — Widersprüche stehen bleiben
Wenn zwei Belege einander widersprechen, verwirft das System keinen von
beiden, sondern markiert den Widerspruch an der betroffenen Wissenseinheit.

Fachliche Uneinigkeit ist ein Lerninhalt, kein Datenfehler. Ein Prüfer darf
danach fragen, eine Diskussionsrunde darf sie austragen.

## 3. Wissenseinheiten

### BIB-10 — Eine Einheit, ein Gedanke
Eine Wissenseinheit trägt Titel, Kurzfassung, ausformulierten Inhalt und die
Liste ihrer Belege. Was sich nicht in einer Kurzfassung sagen lässt, ist
mehr als eine Einheit.

### BIB-11 — Jede Aussage belegt
Das System weist jeder inhaltlichen Aussage einer Wissenseinheit mindestens
einen Beleg zu. Aussagen ohne Beleg werden als **Einordnung** markiert
(TB-1) und sind im ausgelieferten Artefakt als solche erkennbar.

### BIB-12 — Voraussetzungen benennen
Eine Wissenseinheit nennt die Einheiten, die man vorher verstanden haben
sollte. Daraus ergibt sich die Reihenfolge im Lernpfad.

### BIB-13 — Schwierigkeitsgrad
Jede Wissenseinheit trägt einen Schwierigkeitsgrad, damit Formate ihr Niveau
daran ausrichten können.

> **OFFEN (E-7):** Welche Skala? Drei Stufen (Einstieg / Vertiefung /
> Experte) genügen vermutlich und sind leichter konsistent zu vergeben als
> fünf.

## 4. Recherche

### BIB-14 — Recherche ist ein Auftrag
Eine Recherche beginnt mit einer schriftlichen Themenstellung und liefert
Quellen und Belegvorschläge zurück, keine fertigen Wissenseinheiten.

### BIB-14a — Websuche läuft über die Abo-CLI
Der Rechercheur sucht und liest über die Werkzeuge der Anbieter-CLI, die
gezielt freigegeben werden (`claude -p --allowedTools WebSearch WebFetch`).
Es gibt keinen eigenen Suchmaschinen-Zugang und keinen Schlüssel dafür.

Das hält TB-5 auch für die Recherche durch: Suchen und Lesen hängen am selben
Abo wie das Denken.

### BIB-15 — Vorschläge, keine Aufnahme
Recherchierte Quellen und Belege landen in einem Eingang und werden erst
nach Freigabe Teil der Bibliothek.

### BIB-16 — Die Freigabe ist menschlich
Das System nimmt keine Quelle ohne Zustimmung eines Menschen in die
Bibliothek auf.

Das ist die teuerste Regel dieser Spec und die wichtigste. Ohne sie ist
TeachBuddy ein Chatbot mit Zwischenspeicher: Eine unbemerkt aufgenommene
Falschquelle vergiftet ab dann jedes Format, das aus ihr speist, und der
Lernende hat kein Mittel, es zu bemerken (TB-8).

> **OFFEN (E-8):** Bleibt es bei der Einzelfreigabe je Quelle, oder gibt es
> Vertrauensstufen (etwa: Normtexte und Fachverlage automatisch, alles
> andere manuell)? Die Einzelfreigabe ist der ehrliche Start, aber sie wird
> ab dem zweiten Lernpfad zur Bremse.

### BIB-17 — Herkunft der Recherche
Das System hält fest, welcher Agent mit welchem Auftrag und welchem Modell
eine Quelle vorgeschlagen hat.

## 5. Ablage

### BIB-18 — Dateien sind die Wahrheit
Die Bibliothek liegt als Markdown-Dateien mit YAML-Frontmatter in einem
Git-Repo (die Bibliothek), einschließlich der gesicherten Volltexte.
Entschieden in `decisions/E-9.md`.

Der Grund: Sie ist das Wertvollste am Projekt. Sie soll ohne TeachBuddy
lesbar bleiben, sich versionieren und ohne Migration umziehen lassen.

### BIB-18a — Die Freigabe ist ein Diff
Da Agenten in die Bibliothek schreiben (BIB-15), ist die menschliche Freigabe
nach BIB-16 ein `git diff`: Was ein Agent vorschlägt, ist zeilengenau
sichtbar, `git revert` macht es rückgängig.

Das ist der eigentliche Grund für Dateien statt Datenbank. Ein Agenten-Update
in einer Datenbank ist spurlos, solange niemand Audit-Tabellen und eine
Freigabeoberfläche baut.

### BIB-18b — Die Datenbank ist ein Index, keine Wahrheit
Aus den Dateien wird eine SQLite-Datei gebaut, die Kanten und Volltextsuche
(FTS5) bereitstellt. Sie wird **nie von Hand geändert**, liegt nicht im Git
und ist jederzeit aus den Dateien neu baubar.

Ist der Index kaputt, wird er weggeworfen. Läge die Wahrheit in ihm, wäre
jeder Schemafehler eine Migration und jeder Ausfall ein Verlust.

### BIB-18c — Keine Vektoren im ersten Bau
Der Index arbeitet mit Stichwortsuche (FTS5 rankt nach BM25). Einbettungen
kommen erst dazu, wenn BIB-6 nachweislich Dubletten durchlässt, weil dieselbe
Sache unter anderem Namen nicht erkannt wird. Dann lokal und nur beim
Indexieren, nicht als Dauerprozess (TB-6).

### BIB-19 — Änderungen sind nachvollziehbar
Wenn ein Beleg oder eine Wissenseinheit geändert wird, bleibt nachvollziehbar,
was vorher galt. Das leistet die Git-Historie, es braucht kein eigenes
Verfahren.

### BIB-20 — Betroffene Artefakte melden
Wenn sich eine Wissenseinheit ändert, weist das System die daraus erzeugten
Artefakte als veraltet aus.

Ohne diese Regel bricht TB-2: Eine Korrektur in der Bibliothek erreicht die
Formate nie, und der Lernende hört weiter den alten Podcast.

## 6. Die drei Graphen

### BIB-21 — Drei Ebenen, nicht ein Netz
Die Bibliothek trägt drei miteinander verbundene Graphen über denselben
Knoten. Sie werden nicht vermischt, weil sie verschiedene Fragen beantworten:

| Graph | Kanten | beantwortet |
|---|---|---|
| **Evidenz** | Quelle → Fundstelle → Beleg → Wissenseinheit | Worauf stützt sich das? |
| **Begriff** | Begriff setzt Begriff voraus | Was muss vorher erklärt sein? |
| **Didaktik** | Lernziel ← Wissenseinheit, Prüfungsfrage → Lernziel | Ist alles abgedeckt und geprüft? |

Der Wert liegt in ihrer Verbindung. Erst wenn die drei Ebenen aneinander
hängen, lässt sich eine Kette durchlaufen:

```
Quelle → belegt Aussage → erklärt Begriff → erfüllt Lernziel
       → wird in Podcast verwendet → wird durch Prüfungsfrage geprüft
```

Damit werden Fragen beantwortbar, die vorher nicht stellbar waren:
Welche Wissenseinheiten sind nur schwach belegt? Prüfen die Fragen des
Prüfers überhaupt alle Lernziele? Was muss neu geprüft werden, wenn eine
Quelle veraltet?

### BIB-22 — Kanten sind typisiert
Eine Beziehung trägt ihren Typ. Ein untypisierter Verweis ist keine Kante.

Im Einsatz sind: `stützt`, `widerspricht`, `präzisiert`, `ersetzt`,
`handelt_von`, `setzt_voraus`, `dient_lernziel`, `prüft`.

Der Grund: BIB-9 (Widerspruch), BIB-12 (Voraussetzung) und MMP-5 (Querbezug)
sind drei verschiedene Dinge. Ein nackter Verweis kann sie nicht
unterscheiden, und ein Agent sieht den Unterschied nicht, den ein Mensch beim
Lesen erraten würde.

### BIB-23 — Kanten haben eine Gültigkeit
Eine Kante trägt `gilt_ab`, optional `gilt_bis`, eine `zuversicht` und wer
sie gesetzt oder geprüft hat.

Ohne das ist „was muss neu geprüft werden, wenn diese Quelle veraltet" ein
Ratespiel. Mit dem Zeitraum ist es eine Abfrage.

### BIB-24 — Kanten leben im Frontmatter
Kanten stehen in der YAML-Kopfzeile der Datei, die sie ausgehen lässt, nicht
als Verweis im Fließtext.

Fließtext-Verweise lassen sich nicht typisieren und nicht mit Gültigkeit
versehen, ohne den Text unlesbar zu machen.

## 7. Gestalt auf der Platte

```
bibliothek/
  quellen/
    Q-0007/
      quelle.md              Metadaten (BIB-1..5)
      versionen/
        V-2026-09-10.md      gesicherter Wortlaut (BIB-4a)
      fundstellen.md          F-0007-01 … Zitat + Stelle + Version
  belege/
    B-0007-01.md              Aussage + Fundstelle + Gültigkeit
  einheiten/
    WE-0042.md                Frontmatter mit Kanten + Inhalt
  pfade/
    P-01.md                   geordnete Folge
  index.db                    gebaut, nicht im Git
```

### BIB-25 — V1 baut nicht alles
Der erste Bau umfasst Quellen, Quellenversionen, Fundstellen, Belege,
Wissenseinheiten und Lernpfade. **Begriffe und Lernziele als eigene Knoten
kommen später**, wenn ein Format sie braucht (TB-9).

Der Begriffs- und der didaktische Graph sind in BIB-21 beschrieben, damit das
Datenmodell sie später ohne Umbau aufnehmen kann. Gebaut werden sie erst,
wenn der Prüfer die Abdeckungsfrage tatsächlich stellt.

## 8. Vier Ebenen, vier Namen

### BIB-26 — Die Hierarchie und ihre Begriffe
Zwischen dem atomaren Baustein und dem ganzen Thema liegen vier Ebenen. Sie
tragen verschiedene Namen, weil sie verschiedene Dinge sind:

| Ebene | ID | was es ist | Größe |
|---|---|---|---|
| **Wissenseinheit** | `WE-` | ein Gedanke, belegt (BIB-10) | ein Absatz |
| **Lektion** | `L-` | eine Podcast-Folge samt Folie und Fragen | 5 bis 10 Minuten |
| **Kapitel** | `K-` | mehrere Lektionen, hat Mindmap und Diskussionspartner | ein Abschnitt |
| **Lernpfad** | `P-` | mehrere Kapitel | ein Thema |

**Wissenseinheit und Lektion sind nicht dasselbe**, auch wenn beide im
Sprachgebrauch „Einheit" heißen. Eine Wissenseinheit ist der kleinste belegte
Baustein; eine Lektion ist das, was der Lernende hört, und bündelt mehrere
davon. Diese Trennung ist TB-2 auf der Zeitachse: Die Wissenseinheit gehört
der Wissensschicht, die Lektion der Darbietung.

Praktisch heißt das: Wird eine Wissenseinheit korrigiert, sind genau die
Lektionen betroffen, die sie verwenden (BIB-20). Eine Lektion neu zu bauen
kostet einen Vertonungslauf, nicht eine neue Recherche.

### BIB-26a — Ein Abschnitt ist eine Lektion, kein Kapitel
Die Abschnitte eines Lernpfads (A bis M in P-01) sind **Lektionen**. Ein
Abschnitt ist eine Podcast-Folge von 5 bis 10 Minuten, und das ist nach
BIB-26 die Größe einer Lektion.

Bis zum 12.09.2026 hat der Dienst sie als Kapitel ausgegeben. Dadurch bekam
jeder Abschnitt seine eigene Mindmap und seinen eigenen Gesprächspartner —
dreizehn kleine Landkarten statt einer Übersicht.

Rückmeldung vom 12.09.2026:

> „Agent Evaluation ist das Kapitel, und darunter hängen die 13 Lektionen mit
> 13 Podcasts, und das ganze Kapitel aus allen 13 Lektionen bekommt aber eine
> Mindmap als Übersicht und einen Agenten."

**Ein Kapitel steht in `kapitel/K-nn.md`** und nennt seinen Lernpfad und seine
Lektionen in Reihenfolge. Es wird nicht aus Abschnittsbuchstaben erschlossen:
Welche Lektionen zusammengehören, entscheidet der Mensch (BIB-16).

### BIB-26b — Geplante Lektionen werden mitgezählt, aber nicht als Fortschritt
Ein Kapitel zeigt **alle** seine Lektionen, auch die noch nicht gebauten. Nur
die gebauten zu zeigen, ließe das Kapitel fertig aussehen.

Der Fortschritt zählt aber **nur gebaute**. „0 von 13 gehört" wäre keine
Untertreibung, sondern falsch: Zwölf davon gibt es als Folge nicht, also kann
niemand sie gehört haben. Die geplanten stehen getrennt daneben.

### BIB-27 — Die Zuordnung liegt bei der Lektion
Eine Lektion nennt die Wissenseinheiten, aus denen sie besteht, in ihrer
Reihenfolge. Eine Wissenseinheit weiß nicht, in welchen Lektionen sie
vorkommt; das beantwortet der Index (BIB-18b).

Sonst müsste jede Wissenseinheit angefasst werden, wenn eine Lektion neu
geschnitten wird.

## 9. Reichweite und Rückmeldung

### BIB-4b — Volltext, nicht Zusammenfassung
Eine Quellenversion enthält den **Volltext** der Quelle, soweit zugänglich.
Ein Abstract, ein Klappentext oder eine Suchergebnis-Zusammenfassung ist
keine Quellenversion.

Der Grund ist inhaltlich, nicht formal: Ein Abstract trägt den Befund, aber
nicht seine Bedingungen. Wer daraus eine Lektion baut, kann sagen, *dass*
etwas gilt, aber nicht *warum* und *wann nicht*. Genau das ist der
Unterschied zwischen einer Lernbibliothek und einer Sammlung von
Schlagzeilen.

### BIB-4c — Volltext wird geholt, nicht abgerufen
Der Volltext wird als Datei geladen und im Original gelesen (HTML-Fassung wo
vorhanden, sonst PDF über `pdftotext`). Er wird **nicht** über ein
Abrufwerkzeug bezogen, das den Inhalt durch ein Modell zusammenfasst.

Ein zusammengefasster Volltext ist wieder ein Abstract, nur eines, das
niemand geschrieben hat und das sich als Wortlaut ausgibt. Wörtliche Zitate
daraus wären nicht überprüfbar.

### BIB-4d — Die Reichweite steht an der Quelle
Jede Quelle vermerkt, wie weit sie gelesen wurde: `volltext`,
`teilweise` (mit Angabe welcher Abschnitte) oder `nur-abstract`.

`nur-abstract` ist zulässig, wenn der Volltext nicht zugänglich ist. Dann ist
es eine dokumentierte Einschränkung statt einer stillen. Belege aus einer
solchen Quelle tragen höchstens `zuversicht: mittel`.

### BIB-28 — Die Recherche urteilt über die Gliederung
Ein Rechercheauftrag liefert nicht nur Material, sondern auch einen
**Gliederungsbefund**: ob der recherchierte Abschnitt so trägt, wie er
geplant war.

Zu melden ist mindestens:
- welche geplanten Begriffe sich **nicht belegen** ließen
- welche Begriffe in den Quellen **wichtig sind, aber in der Gliederung
  fehlen**
- wo die Gliederung eine Ordnung behauptet, die die Quellen nicht hergeben
- wo zwei geplante Punkte in Wahrheit einer sind

### BIB-29 — Die Gliederung ändert der Mensch
Ein Gliederungsbefund ist ein Vorschlag. Kein Agent ändert einen Lernpfad.

Dieselbe Logik wie BIB-16: Wer das Material sammelt, soll nicht auch
bestimmen, was gelernt wird. Sonst schneidet sich der Lernpfad auf das zu,
was leicht zu finden war.

### BIB-30 — Nicht Belegbares wird gekennzeichnet, nicht weggelassen
Bleibt ein geplanter Begriff unbelegt und soll trotzdem im Lehrtext
vorkommen, wird er als **Sammelbegriff** ausgewiesen und nicht als Fachbegriff
mit Fundstelle behandelt.

Das ist der ehrliche Umgang mit Ordnungsbegriffen, die es in der Literatur so
nicht gibt: Sie sind als Gliederungshilfe nützlich und als belegte Aussage
falsch.
