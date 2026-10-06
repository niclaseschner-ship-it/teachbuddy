# Auftrag: Podcast-Skript

> Auftragsdatei nach AUF-5 / E-2 — anbieterneutral. Läuft nach AUF-16 auf
> GPT (`codex exec`), weil dieser Auftrag Sprache und Ton verlangt.
>
> Der Platz dieser Datei ist nach AUF-5 eigentlich `auftraege/podcast.md`;
> sie liegt hier, weil sie zum Podcast-Bau gehört.

Du schreibst das Sprechskript einer **Podcast-Folge** für eine Lernplattform.
Die Folge ist ein Gespräch zwischen genau zwei Rollen.

## Dein Material

Du bekommst eine Datei `material.md` mit Wissenseinheiten. **Das ist alles,
was du hast, und alles, was du benutzen darfst.** Du recherchierst nicht, du
rufst nichts ab, du greifst nicht auf dein eigenes Wissen über das Thema
zurück. Jede Sachaussage im Skript steht in einer dieser Einheiten.

Jede Aussage im Material trägt Beleg-Marker der Form `[B-0002-01]`.
Einordnungen des Modellierers tragen `[E]`.

## Die Form

Schreibe reines Markdown in genau dieser Form:

    # <Titel der Folge>

    ## <Titel des ersten Abschnitts>

    MODERATOR: Satz oder zwei. [E]
    GAST: Erklärung, so lang sie sein muss. [B-0002-01] [B-0005-03]

    ## <Titel des nächsten Abschnitts>

    MODERATOR: Nachfrage. [B-0001-06]
    GAST: Antwort. [B-0001-06]

Regeln, an denen eine mechanische Prüfung hängt — halte sie genau ein:

1. Jede Sprecherzeile beginnt mit `MODERATOR: ` oder `GAST: `, in
   Großbuchstaben, mit Doppelpunkt und Leerzeichen. Keine anderen Sprecher.
2. **Jede** Sprecherzeile endet mit mindestens einem Marker. Entweder
   `[B-nnnn-nn]` für eine belegte Aussage (mehrere nebeneinander, wenn sie
   auf mehreren Belegen steht) oder `[E]` für eine Einordnung.
   *Eine Zeile ohne Marker lässt den Auftrag scheitern.*
3. Du erfindest keine Marker. Ein `[B-…]`, das nicht im Material steht,
   lässt den Auftrag scheitern. Wenn du eine Aussage nicht belegen kannst,
   schreibe sie nicht.
4. Du benutzt eckige Klammern für nichts anderes als Marker.
5. Abschnitte trennst du mit `## <Titel>`. Mindestens drei: Der erste ist
   die Eröffnung, der letzte die Zusammenfassung, dazwischen der Inhalt.
   Der Titel eines Abschnitts wird dem Hörer als Kapitelmarke angezeigt —
   schreibe ihn kurz und sprechend, nicht als Satz, und in normaler
   deutscher Groß- und Kleinschreibung („Was gemessen wird", nicht „Was
   Gemessen Wird").
6. Sonst nichts: keine Regieanweisungen, keine Klammern mit Tonfall, keine
   Aufzählungen, keine Fettschrift im gesprochenen Text.
7. **Die beiden wissen nichts von diesem Auftrag.** Im gesprochenen Text
   kommen die Wörter **Material, Auftrag, Wissenseinheit, Beleg, Marker,
   Quellenlage, übergeben** nicht vor, und auch keine Umschreibung davon. Sie
   sind zwei Menschen in einem Gespräch, keine zwei Werkzeuge in einer
   Pipeline. Der Hörer kennt diese Begriffe nicht und sie gehen ihn nichts an.

   *Das ist der Fehler, der diese Fassung ausgelöst hat.* In einer fertigen,
   vertonten Folge sagte der Moderator, er habe keine Beispiele in den Daten.
   In achtzehn von siebenundvierzig Folgen steht ein ganzer gesprochener
   Abschnitt, in dem die beiden über ihre Arbeitsanweisung reden.

   **Der Unterschied, auf den es ankommt, ist, worüber der Satz redet.**
   „Dazu gibt es bisher kaum belastbare Zahlen" ist eine Aussage über die
   Sache und gehört hinein. „Das steht nicht in unserem Material" ist eine
   Aussage über uns und gehört nicht hinein.

## Die beiden — das ist der wichtigste Abschnitt

Das sind **zwei Menschen mit verschiedener Sprache**, nicht zwei Funktionen.
Wenn beide dasselbe Deutsch reden und sich nur in der Länge unterscheiden,
klingt die Folge wie ein aufgeteilter Vortrag, und genau das ist der Fehler,
den diese Fassung abstellen soll.

### GAST — die Praktikerin, die es selbst gebaut hat

Sie erklärt, trägt den Inhalt und redet in längeren Zügen. Sie spricht **aus
Erfahrung und sagt „ich"**: was sie überrascht hat, wo sie es zuerst falsch
gemacht hat, was sie inzwischen anders macht. Sie sagt „das weiß ich nicht"
und „da wird es dünn", wo es so ist.

Sie redet in **Hauptsätzen mit handelnden Personen**. Nicht „die Bewertung
der Ausgabe erfolgt durch ein Modell", sondern „ein zweites Modell liest die
Antwort und benotet sie".

### MODERATOR — der informierte Laie, der nicht lockerlässt

Er führt: eröffnet mit dem Thema, fragt nach, leitet über, fasst am Ende
zusammen. Er kennt das Feld, aber **nicht dieses Thema**, und er darf zugeben,
dass er etwas noch nicht hat — „Moment, das habe ich noch nicht."

**Sein wichtigster Zug:** Wenn der Gast einen Fachbegriff eingeführt hat, sagt
der Moderator ihn **in eigenen, einfachen Worten nach** und lässt sich
bestätigen oder korrigieren. Das ist keine Höflichkeitsfloskel, sondern die
Stelle, an der die Folge für den Hörer auf eine zweite Ebene kommt. Mach das
mehrmals je Folge, an den schwierigen Begriffen.

    GAST: … das nennt sich Sampling. [B-0189-01]
    MODERATOR: Also würfelt es, grob gesagt — es rechnet nicht ein Ergebnis
    aus, sondern zieht eins? [E]
    GAST: So ungefähr, mit einer Einschränkung: … [B-0189-02]

Er redet **deutlich weniger** als der Gast — höchstens ein Viertel des Textes.
Seine Fragen sind kurz, oft ein Satz.

Er stellt **keine Sachfrage, deren Antwort nicht im Material steht.** Er darf
zuspitzen und um ein Beispiel bitten. Er darf nicht fragen „Und wie ist das
bei X?", wenn zu X nichts dasteht.

## Der Ton

Es wird gehört, nicht gelesen — beim Gehen, beim Kochen, beim Fahren.

**Die Sätze kurz zu halten reicht nicht.** Das war in den bisherigen Folgen
erfüllt (im Schnitt elf Wörter) und sie klangen trotzdem wie vorgelesen. Es
lag an vier Dingen, und die sind hier die Regeln:

1. **Sag den Fachbegriff, dann sag ihn nochmal einfach.** Beim ersten
   Auftreten steht er in seiner **genauen Form** — der Begriff bleibt, er wird
   später gebraucht. Direkt danach einmal in Alltagswörtern, am besten als
   Nachfrage des Moderators. Die einfache Fassung steht **daneben, nie an
   seiner Stelle**. Geht sie über den Beleg hinaus, trägt sie `[E]`.
2. **Kein Nominalstil.** Vermeide Wörter auf `-ung`, `-heit`, `-keit`, wo ein
   Verb geht, und Passiv, wo jemand handelt. Nicht „die Vermischung von
   Anweisung und Daten ist ein architekturales Merkmal", sondern „Anweisung
   und Daten laufen durch denselben Kanal, und so ist das Ding gebaut". Nicht
   „deterministische Bestanden-Durchgefallen-Zusicherungen gelten als
   ungeeignet", sondern „ein festes Bestanden oder Durchgefallen taugt da
   meistens nicht".
3. **Fang keine Zeile mit „Genau", „Ja", „Richtig" oder „Absolut" an.** Wer
   zustimmt, zeigt es am Inhalt. In den bisherigen Folgen begann jede zweite
   Gast-Zeile so, und das ist das Gegenteil von Charakter.
4. **Eine Frage endet mit einem Fragezeichen**, vor dem Marker. Die
   Sprachausgabe liest sonst mit fallender Stimme, und ein vorgetragener Satz
   klingt anders als eine Frage.

- Gesprochene Sätze. Kurz genug, dass man sie beim ersten Hören versteht.
- **Keine Quellenangaben im gesprochenen Text.** Sag nicht „laut Zheng und
  Kollegen 2023". Der Hörer darf voraussetzen, dass alles belegt ist. Ein
  Name gehört nur dann hinein, wenn über ihn gestritten wird und das zum
  Verständnis gehört.
- Zahlen sparsam und ausgeschrieben, wie man sie sagt: „achtundneunzig
  Prozent", nicht „98,8 %". Eine Zahl, die man sich nicht merken kann,
  lässt du weg — sie steht in der Handreichung.
- Wo das Material selbst unsicher ist oder sich widerspricht, sagst du das.
  Ein geglätteter Widerspruch ist eine Erfindung.

## Der durchgerechnete Fall (POD-16)

**Jede Folge wendet ihre Begriffe auf einen benannten, wirklichen Fall an.**
Nicht als Beispielsatz nebenbei, sondern als eigener Abschnitt, meist gegen
Ende: Man nimmt einen konkreten Gegenstand und geht mit dem eben eingeführten
Vokabular durch ihn hindurch.

Rückmeldung nach dem ersten Hören, 12.09.2026: „Stark, gute Theorie, aber schwer
fassbar. Interessant wäre, wenn wir die Theorie ganz konkret an einem
Beispiel einordnen. Zum Beispiel bei den Benchmarks mal einem erklären mit
dem eingeführten Fachvokabular."

Eine Taxonomie, die man nicht an etwas anlegen kann, bleibt Vokabeln lernen.

**Vier Bedingungen:**

1. **Benannt und wirklich.** „SWE-bench", nicht „ein Benchmark". Nimm, was im
   Material vorkommt.
2. **Belegpflichtig.** Was du über den Fall sagst, trägt seine Marker wie
   jeder andere Satz.
3. **Die Zuordnung ist eine Einordnung** und trägt `[E]`. Dass die
   Aufgabenstellung eines Benchmarks die „Anfrage" ist und das Repository die
   „Umgebung", steht in keiner Quelle. Das ist die Ordnung, die *wir*
   anlegen, und sie wird als solche gesprochen: „wenn wir das mit unserem
   Vokabular durchgehen …", nicht „die Forschung zeigt".
4. **Kein neues Vokabular.** Der Fall wendet an, was die Folge eingeführt hat.
   Brauchst du dort einen neuen Begriff, hast du ihn vorher vergessen.

**Der Gast führt durch den Fall, der Moderator hakt ein**, wo die Zuordnung
nicht glatt aufgeht. Gerade die Stellen, an denen das Vokabular *nicht*
greift, sind die lehrreichen — sie zu verschweigen macht den Fall zur
Werbung.

**Findest du keinen benannten Fall, lass den Abschnitt weg — wortlos.** Weder
der Moderator noch der Gast erwähnen, dass hier einer fehlen würde. Eine Folge
ohne durchgerechneten Fall ist schwächer; eine Folge, in der zwei Leute
darüber reden, dass ihnen einer fehlt, ist kaputt (Regel 7).

Erfinde erst recht keinen.

## Ein Bild oder eine kleine Geschichte (POD-19)

Der durchgerechnete Fall ist die **Probe**, ob die Begriffe tragen. Daneben
braucht jede Folge mindestens eine Stelle, an der die Sache **anschaulich**
wird — den **Haken**, an dem sie hängen bleibt:

- ein Vergleich, der ein Bild gibt,
- eine Zahl, die man weitererzählt („tausend gleiche Anfragen, achtzig
  verschiedene Antworten"),
- eine kurze Erfahrung des Gastes, wo ihn etwas erwischt hat,
- der Moment, in dem etwas gegen die Erwartung läuft.

**Erfunden wird dabei nichts.** Der Stoff steht meistens schon im Material und
wird nur nicht gehoben — eine überraschende Messung ist bereits eine
Geschichte, sie muss nur so erzählt werden. Ein Vergleich, der über den Beleg
hinausgeht, ist eine Einordnung und trägt `[E]`. Eine ausgedachte Anekdote aus
dem Leben des Gastes ist eine Erfindung und damit derselbe Fehler wie ein
erfundener Beleg.

Die Erfahrung des Gastes darf **nur die Haltung zur Sache** betreffen, nicht
die Sache selbst: „Das hat mich zuerst geärgert" ist erlaubt, „bei uns lag die
Trefferquote bei siebzig Prozent" nicht, wenn das nicht im Material steht.

## Die Länge

Die fertige Folge muss **zwischen fünf und zehn Minuten** dauern. Gesprochen
werden rund 150 Wörter je Minute — ziele auf **900 bis 1300 Wörter**
gesprochenen Text. Weniger ist zu dünn, mehr wird abgelehnt.

## Wenn du den Auftrag nicht erfüllen kannst

Reichen die Einheiten für eine ganze Folge nicht — zu wenig, zu
zusammenhanglos, kein roter Faden —, dann schreibe **kein dünnes Skript**.
Schreibe stattdessen als **einzigen Inhalt** der Zieldatei:

    # ABLEHNUNG

    <in zwei, drei Sätzen: was fehlt und warum es so nicht trägt>

**Das ist eine Nachricht an die Maschine, die dich aufgerufen hat, kein Teil
der Folge.** Entweder du schreibst ein vollständiges Skript, oder du schreibst
diese Ablehnung — nie beides und nie eine Mischung. Es gibt keinen Abschnitt
*innerhalb* einer Folge, in dem die Lage des Materials besprochen wird; eine
solche Überschrift hat in einem Skript nichts zu suchen (Regel 7).

Eine ehrliche Absage ist besser als eine Folge, die nichts sagt.

## Wohin

Schreibe das fertige Skript in die Datei `skript.md` im aktuellen
Verzeichnis. Sonst legst du nichts an und änderst nichts. Gib am Ende keine
Zusammenfassung aus — die Datei ist das Ergebnis.
