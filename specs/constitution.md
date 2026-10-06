# TeachBuddy — Constitution

Übergeordnete Prinzipien. Sie ändern sich selten und binden jede Spec in
`specs/`. Wo eine Spec einem Prinzip widerspricht, gewinnt das Prinzip.

## North Star

> **Man lernt nur, was belegt ist.**

TeachBuddy ist keine Maschine, die plausibel klingende Sätze produziert.
Es ist ein Werkzeug, das recherchiertes, geprüftes Wissen in die Form
bringt, in der ein bestimmter Mensch es aufnimmt.

## TB-1 — Kein Satz ohne Herkunft

Jede inhaltliche Aussage in einem ausgelieferten Artefakt führt auf mindestens
eine Quelle in der Bibliothek zurück. Was sich nicht belegen lässt, wird
entweder als **Einordnung** gekennzeichnet oder es wird nicht ausgeliefert.

Das ist die Regel, aus der alles andere folgt: die Trennung von Bibliothek
und Formaten, der Prüfschritt in der Recherche, die Quellenangabe in jeder
Handreichung.

## TB-2 — Wissensschicht und Darbietungsschicht sind getrennt

Die Bibliothek beschreibt, **was gilt**. Ein Format beschreibt, **wie es
vermittelt wird**. Ein Format erfindet keinen Inhalt hinzu und die Bibliothek
kennt kein Format.

Der Nutzen ist praktisch: Ein neues Lernformat kostet einen neuen Agenten und
keine neue Recherche. Wenn ein Beleg korrigiert wird, sind alle Formate
gleichzeitig betroffen und werden neu erzeugt, statt einzeln nachgepflegt.

## TB-3 — Lerntypen sind austauschbar, der Kern ist es nicht

Die vier Startformate (Podcast, Diskussionsrunde, Prüfer, Mindmap) sind
die bevorzugte Zugänge, nicht die Definition des Systems. Jedes Format ist
ein austauschbares Modul hinter einem gemeinsamen Vertrag (AUF-2). Ein fünftes
Format hinzuzufügen darf keine Änderung an der Bibliothek erfordern.

## TB-4 — Erzeugen ist teuer, Ausliefern ist billig

Jedes Artefakt wird **einmal** erzeugt, gespeichert und danach beliebig oft
ausgeliefert. Nichts wird beim Öffnen der App neu generiert. Das begrenzt die
Kosten, macht die App offline-tauglich und hält die Antwortzeit vorhersagbar.

Ausnahme sind Rückfragen im Gespräch (DIS), die naturgemäß live entstehen.

## TB-5 — Erzeugen läuft über Abos, Erleben über APIs

Die Trennlinie liegt nicht zwischen Anbietern, sondern zwischen zwei Arten
von Arbeit:

**Was TeachBuddy baut, läuft über die Abo-Zugänge.** Recherche, Modellierung,
Prüfung, Podcast-Skripte, Prüfungsfragen, Grafiken. Das sind Aufträge im
Hintergrund: Sie dürfen Minuten dauern, sie laufen nachts, niemand wartet.
Dafür sind `claude -p` und `codex exec` da, beide ohne API-Schlüssel, beide
erprobt. **Hier entstehen keine laufenden Kosten.**

**Was der Lernende erlebt, läuft über bezahlte Schnittstellen.** Sprachausgabe
des Podcasts und das Gespräch mit dem Lernpartner. Der Grund ist nicht
Bequemlichkeit: Kein Abonnement liefert Sprachsynthese oder ein flüssiges
Gespräch programmatisch. Es gibt keinen offiziellen Weg, das
ChatGPT-Sprachchat-Erlebnis in eine eigene App einzubetten, und ein
Kommandozeilen-Werkzeug, das für Programmieraufgaben gebaut ist, ist kein
Gesprächspartner.

Diese Trennung ist auch ökonomisch richtig herum: **Bauen ist umsonst, Nutzen
kostet.** Ein Lernpfad, der einmal entsteht und hundertmal gehört wird,
verursacht seine Kosten dort, wo auch der Nutzen liegt.

Was daraus in jeder Spec gilt:

- **Ein Erzeugungsaufruf ist ein Unterprozess, kein HTTP-Request.** Latenz in
  Sekunden bis Minuten. Erzeugung läuft als Auftrag, nicht auf Knopfdruck
  (TB-4).
- **Es gibt Nutzungsgrenzen.** Massenhafte Parallelität ist nicht möglich
  (AUF-10).
- **Ein Abo ist personengebunden.** TeachBuddy ist ein Werkzeug für eine Person, die es selbst betreibt.
  Es als Dienst für fremde Nutzer zu betreiben, wäre eine andere Frage mit
  anderer Antwort.
- **Strukturierte Ausgaben muss TeachBuddy selbst erzwingen.** Die CLIs geben
  Text zurück; Schema-Treue entsteht durch Prompt plus Nachprüfung.
- **Jede bezahlte Schnittstelle braucht eine Kostenbremse.** Wo pro Minute
  oder pro Zeichen abgerechnet wird, wird mitgeschrieben, was verbraucht
  wurde (POD-7a), und es gibt eine Obergrenze, an der abgebrochen wird.

## TB-6 — Der Server ist der Auslieferer, nicht die Denkmaschine

TeachBuddy läuft auch auf kleiner Hardware, etwa einem Raspberry Pi neben
anderen Diensten. **Speicher ist dort der Engpass**, nicht die Platte und
nicht die CPU.

Was auf dem Server läuft: die Bibliothek, die Ablage der Artefakte, das
Zusammenfügen der Audiodateien und die Auslieferung an die App. Was nicht dort
läuft: ein selbst gehostetes Sprachmodell und die Sprachsynthese.

## TB-7 — Zwei Köpfe gleichzeitig, hinter einer Schnittstelle

Kein Modul spricht direkt mit einem Anbieter. Zwischen TeachBuddy und jedem
externen Werkzeug (Denken, Sprachsynthese, Suche) liegt eine schmale
Provider-Schnittstelle, hinter der sich der Anbieter wechseln lässt.

Beim Denken ist das mehr als Austauschbarkeit: **Claude und GPT laufen
gleichzeitig im Regelbetrieb**, damit Produzent und Prüfer nie derselbe Kopf
sind (AUF-15). Die Schnittstelle muss deshalb zwei aktive Anbieter tragen,
nicht einen konfigurierten von zweien.

Der Grund ist nicht Theorie: Preise, Modellnamen, CLI-Flags und
Verfügbarkeiten ändern sich schneller als dieses Projekt.

## TB-8 — Ehrlich über Grenzen

Wo TeachBuddy etwas nicht weiß, sagt es das. Ein Prüfer, der eine Antwort
nicht bewerten kann, sagt es. Eine Diskussionsrunde, die eine Rückfrage nicht
aus der Bibliothek beantworten kann, sagt es und bietet an, die Frage in die
Recherche zurückzugeben.

Eine erfundene Antwort ist in einer Lern-App schlimmer als keine Antwort: Der
Lernende hat kein Mittel, den Fehler zu bemerken, und behält ihn.

## TB-9 — Nichts auf Vorrat

Eine Spec-Datei, ein Modul, ein Konfigurationswert entsteht, wenn er gebraucht
wird — nicht, weil er später gebraucht werden könnte. Leere Abschnitte,
ungenutzte Abstraktionen und Formate ohne Nutzer sind Schulden.
