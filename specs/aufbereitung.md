# Aufbereitung — Spec     (ID-Präfix: AUF)

> Status: Entwurf · trägt TB-2, TB-3, TB-4, TB-5

## Problem

Aus derselben Wissenseinheit soll ein Podcast, eine Expertenrunde, ein
Prüfungsgespräch und eine Mindmap werden können. Wenn jedes Format seinen
eigenen Weg zum Wissen sucht, entstehen vier Wahrheiten, die auseinanderlaufen.

Diese Spec beschreibt den **gemeinsamen Vertrag**, an den sich jedes Format
hält, und das **Agenten-Modell**, das die Arbeit macht.

## 1. Das Agenten-Modell

### AUF-1 — Sechs Rollen, klar geschnitten

TeachBuddy ist multiagentisch, weil die Arbeitsschritte verschiedene Haltungen
verlangen. Ein Rechercheur, der zugleich prüft, findet nichts Unangenehmes.

| Rolle | Aufgabe | Darf schreiben |
|---|---|---|
| **Rechercheur** | Quellen finden, Fundstellen und Belege vorschlagen | Eingang |
| **Modellierer** | Belege zu Wissenseinheiten bündeln, Kanten setzen, Reihenfolge legen | Eingang |
| **Prüfer** | Ableitungen gegen den Wortlaut halten, Gegenbelege suchen, Veraltetes und Übertreibungen finden | Beanstandungen |
| **Vorbereiter** | Ergebnisse bündeln, Vollständigkeit prüfen, die Vorlage für die Freigabe schreiben | Eingang |
| **Format-Agent** | eine Wissenseinheit in ein Artefakt gießen | Artefakte |
| **Gesprächspartner** | Rückfragen des Lernenden beantworten | nichts |

Zwei Schnitte tragen diese Tabelle:

**Produktion und Kontrolle sind getrennt.** Der Prüfer ist absichtlich eine
eigene Rolle. Wer eine Quelle gefunden oder eine Wissenseinheit geschnitten
hat, hat ein Interesse daran, dass sie taugt. Ein Berater/Antiberater-Paar
ist dasselbe Muster, und es trägt.

**Niemand prüft sich selbst.** Der Modellierer gibt seine eigenen Belege nicht
frei, und der Prüfer räumt seine eigenen Beanstandungen nicht selbst ab.

### AUF-1a — Kein Agent gibt frei
Keine Rolle in AUF-1 schreibt in die Bibliothek. Der Vorbereiter legt eine
Vorlage, der Mensch gibt frei (BIB-16, BIB-18a).

Das ist die Stelle, an der ein naheliegender Zuschnitt bricht: Ein
„Orchestrator mit finaler Freigabe" wäre bequem und ist genau das, was E-9
ausschließt. Sobald ein Agent committet, ist der Diff kein Prüfwerkzeug mehr,
sondern ein Protokoll dessen, was bereits geschehen ist. Die ganze Begründung
für Dateien statt Datenbank hinge dann in der Luft.

Der Vorbereiter macht die Freigabe **billig**, nicht überflüssig: Er bündelt,
er nennt offene Beanstandungen, er schreibt in einem Satz, was sich ändert.
Was er nicht tut, ist `git commit`.

### AUF-1b — Beanstandet heißt blockiert
Eine Beanstandung des Prüfers verschwindet nicht dadurch, dass jemand sie
übergeht. Sie wird entweder durch neue Recherche ausgeräumt und erneut
geprüft, oder sie steht im Freigabevorschlag als offener Punkt.

### AUF-1c — Der Ablauf
```
Rechercheur → Modellierer → Prüfer → Vorbereiter → Mensch → Bibliothek
                   ▲                     │
                   └──── Rückschleife ───┘
                     (Prüfer beanstandet: neue Recherche,
                      Korrektur, erneute unabhängige Prüfung)
```

### AUF-2 — Ein Format-Agent kennt nur den Vertrag
Ein Format-Agent bekommt Wissenseinheiten samt Belegen und liefert ein
Artefakt. Er greift nicht selbst auf Quellen zu und nicht auf die Bibliothek.

Damit kostet ein fünftes Format einen Agenten und keine Änderung an der
Wissensschicht (TB-3).

### AUF-3 — Kein Agent erfindet Inhalt
Wenn ein Format-Agent eine Aussage ausspielt, die in keiner übergebenen
Wissenseinheit steht, ist das ein Fehler und kein Stil. Der Prüfschritt
(AUF-8) findet ihn.

### AUF-4 — Agenten laufen über die Abo-CLI
Ein Agentenaufruf ist ein Unterprozess der Anbieter-CLI mit Auftrag,
Eingabematerial und erwarteter Ausgabeform. Es gibt keinen API-Schlüssel im
System (TB-5).

### AUF-5 — Ein Agent hat einen schriftlichen Auftrag
Jede Rolle ist eine versionierte Datei im Repo, keine im Code verstreute
Zeichenkette. Wer das Verhalten eines Agenten ändern will, ändert seinen
Auftrag und sieht die Änderung im Diff.

Entschieden in `decisions/E-2.md`: **anbieterneutrale Auftragsdateien**
(`auftraege/<rolle>.md`), die TeachBuddy an den jeweiligen Kopf reicht. Keine
Claude-Code-Subagenten, weil eine Rolle nach AUF-17 den Kopf wechseln können
muss.

## 2. Der Auftrag

### AUF-6 — Erzeugung ist ein Auftrag mit Zustand
Das Erzeugen eines Artefakts ist ein benannter Auftrag mit einem der Zustände
`offen`, `läuft`, `fertig`, `gescheitert`. Die App fragt den Zustand ab,
statt zu warten.

Das ist die unmittelbare Folge aus TB-5: Ein Podcast entsteht in Minuten,
nicht in einer HTTP-Anfrage.

### AUF-7 — Ein Auftrag ist wiederholbar
Wenn ein Auftrag scheitert, lässt er sich mit identischer Eingabe erneut
starten, ohne dass ein halbfertiges Artefakt zurückbleibt.

### AUF-8 — Belegprobe vor der Auslieferung
Bevor ein Artefakt als `fertig` gilt, prüft das System, ob jede inhaltliche
Aussage darin einer übergebenen Wissenseinheit zuzuordnen ist. Nicht
zuordenbare Aussagen werden gemeldet und der Auftrag gilt als `gescheitert`.

Das ist die technische Umsetzung von TB-1. Ohne AUF-8 ist die ganze
Bibliothek Dekoration: Das Modell würde am Ende doch aus dem eigenen
Gedächtnis erzählen, und niemand würde es merken.

Entschieden in `decisions/E-3.md`: Die Probe ist **mechanisch**, kein
zweiter Agentenaufruf. Wie, steht in AUF-8a bis AUF-8c.

### AUF-8a — Jeder Sinnabschnitt trägt einen Marker
Ein Format-Agent liefert seinen Text so, dass jeder Sinnabschnitt am Ende
einen Marker trägt: `[B-<beleg-id>]` für eine belegte Aussage, mehrere
nebeneinander wenn sie auf mehreren Belegen steht, `[E]` für eine Einordnung
nach AUF-13.

Was ein Sinnabschnitt ist, legt jedes Format für sich fest: beim Podcast die
Sprecherzeile, in der Handreichung der Folienpunkt, beim Prüfer die Frage
samt Musterantwort, in der Mindmap der Knoten.

### AUF-8b — Auflösen oder scheitern
Vor der Freigabe löst das System jeden `[B-…]`-Marker gegen die übergebenen
Wissenseinheiten auf. Ein nicht auflösbarer Marker, ein Marker auf eine nicht
übergebene Einheit oder ein Sinnabschnitt ohne jeden Marker lässt den Auftrag
scheitern (AUF-6).

Der Abschnitt ohne Marker ist der wichtigste der drei Fälle: Genau so sähe
eine frei erfundene Passage aus.

### AUF-8c — Marker sind Metadaten, kein Inhalt
Marker werden vor der Vertonung und vor der Anzeige entfernt. Der Lernende
sieht sie nur dort, wo eine Spec sie ausdrücklich vorsieht (POD-14).

Ohne diese Regel liest die Sprachausgabe „B 17" mitten im Satz vor.

### AUF-9 — Artefakte kennen ihre Herkunft
Ein Artefakt speichert, aus welchen Wissenseinheiten in welchem Stand es
erzeugt wurde, mit welchem Auftrag und mit welchem Modell.

Daraus folgt BIB-20: Ändert sich eine Einheit, ist auffindbar, welche
Artefakte veraltet sind.

### AUF-10 — Aufträge laufen nacheinander
Das System führt nicht mehr als eine begrenzte Zahl von Agentenaufrufen
gleichzeitig aus. Der Standard ist eins.

Auf einem kleinen Server, auf dem noch andere Dienste Speicher halten, ist
paralleles Erzeugen kein
Geschwindigkeitsgewinn, sondern ein Abschuss.

## 3. Der gemeinsame Format-Vertrag

### AUF-11 — Jedes Artefakt trägt dieselbe Hülle
Titel, Lernpfad und Wissenseinheiten, aus denen es stammt, Erzeugungsdatum,
Format, Zustand, und die Liste der verwendeten Quellen.

### AUF-12 — Jedes Format hat eine Quellenliste
Unabhängig von der Form endet jedes Artefakt mit den Quellen, aus denen es
gespeist ist, in zitierfähiger Form.

### AUF-13 — Einordnungen sind gekennzeichnet
Wo ein Format über die Belege hinausgeht, um verständlich zu bleiben
(Beispiel, Analogie, Überleitung), ist das im Artefakt als Einordnung
erkennbar und nicht als belegte Aussage.

### AUF-14 — Ein Format darf ablehnen
Wenn die übergebenen Wissenseinheiten für ein Format nicht taugen, liefert
der Agent eine Begründung statt eines dünnen Artefakts.

Eine Mindmap aus einer einzigen Wissenseinheit ist keine Mindmap. Ein
Prüfungsgespräch über Material ohne Prüfbares ist Zeitverschwendung. Lieber
eine ehrliche Absage (TB-8).

## 4. Zwei Köpfe

### AUF-15 — Zwei Anbieter gleichzeitig, nicht wahlweise
TeachBuddy fährt **beide** Abo-Zugänge im Regelbetrieb: `claude -p` und
`codex exec`. Das ist kein Ausweichen für den Ausfall des einen, sondern die
Arbeitsweise.

Der Grund ist methodisch: **Ein Modell, das seinen eigenen Text prüft, hat
einen blinden Fleck.** Es hält für plausibel, was es beim Schreiben plausibel
fand, und findet den Fehler genau dort nicht, wo er entstanden ist. Ein
zweiter Kopf bricht das.

Praktischer Nebeneffekt unter TB-5: Die Last verteilt sich auf zwei
Nutzungsgrenzen statt auf eine.

### AUF-16 — Wer was macht
Die Zuordnung folgt den Stärken, nicht dem Zufall:

| Rolle | Kopf | warum |
|---|---|---|
| Rechercheur | Claude | Sorgfalt, Struktur, Belegdisziplin |
| Modellierer | Claude | Kanten, Ontologie, Ganzheitlichkeit |
| Prüfer | **GPT** | Gegenpol zu beiden Produzenten |
| Vorbereiter | Claude | Zusammenführen über den ganzen Vorgang |
| Podcast, Diskussionsrunde | **GPT** | Sprache und Ton |
| Prüfer-Fragen, Mindmap | Claude | Struktur und Abdeckung |
| Gegenlesen der Format-Texte | Claude | Gegenpol zum Format-Agenten |

Daraus ergibt sich eine Symmetrie, die den Punkt trägt:

```
Bibliotheksseite:  Claude produziert  →  GPT prüft
Formatseite:       GPT produziert     →  Claude prüft
```

Auf beiden Seiten sitzt der Prüfer in einem anderen Kopf als der Produzent.

### AUF-17 — Die Zuordnung steht in der Konfiguration
Welche Rolle auf welchem Kopf läuft, ist ein Konfigurationswert je Rolle,
keine im Code verdrahtete Entscheidung.

Die Zuordnung aus AUF-16 ist eine begründete Vermutung über Modellstärken,
kein Naturgesetz. Sie muss sich ändern lassen, wenn eine Probe das Gegenteil
zeigt oder ein Modellwechsel die Lage verschiebt.

### AUF-18 — Modell und Fassung werden mitgeschrieben
Jedes Ergebnis hält fest, welcher Kopf in welcher Fassung es erzeugt hat
(AUF-9). Bei Beanstandungen zusätzlich, welcher Kopf beanstandet hat.

Ohne das ist nach einem Modellwechsel nicht mehr erklärbar, warum der Podcast
aus dem Frühjahr anders klingt als der von heute.

### AUF-18a — Die Fassung der Pipeline wird mitgeschrieben
AUF-18 hält fest, **welcher Kopf** ein Ergebnis erzeugt hat. Das genügt
nicht: Am 13.09.2026 sind an einem einzigen Tag drei Nachbesserungen an der
Podcast-Pipeline gelaufen, alle mit demselben Modell. Danach lagen Folgen aus
drei Ständen im Regal, und an einer fertigen `folge.mp3` war nicht zu
erkennen, welcher.

Jede erzeugte Folge hält deshalb zusätzlich fest:

- die **Fassung der Pipeline** als Zahl (`podcast/fassung.py`),
- den **Tag der Erzeugung**,
- den **Stand des Auftragstexts**, aus dem sie entstand.

Die Fassung steigt, wenn sich ändert, *wie* eine Folge entsteht — der
Auftragstext oder eine blockierende Probe. Nicht, wenn sich das Material
ändert; dafür trägt der Auftrag den Stand der Einheiten (AUF-7).

Die Zahl wird von Hand gepflegt, es gibt keinen Build-Schritt (E-5). **Damit
sie nicht lügt**, hält das Register den Stand des Auftragstexts fest, bei dem
die Fassung festgelegt wurde; weicht die Datei davon ab, meldet der Bau das.
Eine Fassungsnummer, die nicht mehr zum Auftrag passt, ist schlimmer als
keine — sie behauptet etwas Falsches über die Folge.

**Wozu es wirklich da ist:** Ohne Fassung ist eine Rückmeldung nicht zu
deuten. „Klingt sperrig" heißt etwas anderes, wenn die Folge zwei
Nachbesserungen alt ist. Deshalb schreibt OBF-19 die Fassung an jede
Rückmeldung.

Rückmeldung vom 13.09.2026: „sag mir auch, wann die Folge gemacht wurde bzw. welche
Verbesserungen sie schon drin hat. Also musst du anfangen die Pipeline zu
versionieren."

### AUF-19 — Aufrufe sind read-only, wo es geht
Der Prüfer läuft ohne Schreibrechte auf das Dateisystem
(`codex exec --sandbox read-only`). Er liefert Befunde, keine Änderungen.

### AUF-20 — Fällt ein Kopf aus, wird nicht ersetzt
Wenn ein Anbieter seine Nutzungsgrenze meldet oder nicht erreichbar ist,
scheitert der Auftrag mit Klartext (DIS-13). Der andere Kopf springt **nicht**
ein.

Ein Prüfer, der im selben Kopf wie der Produzent läuft, weil der andere gerade
nicht konnte, sieht aus wie eine Prüfung und ist keine. Lieber ein Auftrag,
der wartet, als eine Freigabe, die auf einer Scheinprüfung steht.

## 5. Wenn die Pipeline eine Lücke findet

### AUF-21 — Lücken werden gemeldet, nicht stillschweigend gefüllt
Stellt eine Rolle fest, dass Material fehlt, das der Abschnitt braucht, meldet
sie das als Befund (BIB-28). Sie füllt die Lücke nicht selbst und schneidet
den Abschnitt auch nicht darauf zurecht.

### AUF-22 — Der Vorbereiter entscheidet über Nachlieferung
Der Vorbereiter (AUF-1) entscheidet, ob eine gemeldete Lücke **vor** der
Freigabe geschlossen wird oder ob der Abschnitt ohne sie ausgeliefert und die
Lücke kenntlich gemacht wird (BIB-30).

Maßstab ist eine Frage: **Ist das Kapitel ohne dieses Material in sich
schlüssig?** Ein Kapitel, dem der Kern fehlt, wird nachrecherchiert. Ein
Kapitel, dem eine Randfrage fehlt, wird ausgeliefert und die Lücke vermerkt.

Diese Entscheidung ist **Steuerung, keine Freigabe**. Der Vorbereiter darf
einen Rechercheauftrag auslösen und einen Abschnitt zurückstellen. Er darf
nichts in die Bibliothek aufnehmen (AUF-1a, BIB-16). Die Grenze verläuft
zwischen *„wir holen das nach"* und *„das gilt jetzt"*.

### AUF-23 — Die Entscheidung wird begründet festgehalten
Jede Nachlieferungsentscheidung notiert, welche Lücke gemeldet wurde, wie
entschieden wurde und warum.

Ohne diese Spur ist später nicht mehr erkennbar, ob ein dünner Abschnitt eine
bewusste Entscheidung war oder ein übersehener Befund.
