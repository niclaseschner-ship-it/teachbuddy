# Diskussionsrunde mit Experten — Spec     (ID-Präfix: DIS)

> Status: Entwurf · folgt AUF-2, AUF-11..AUF-14

## Problem

Nach dem Podcast weiß man, was gilt. Was fehlt, ist das Gefühl dafür, **wo es
strittig ist** und **warum es so und nicht anders gemacht wird**. Das lernt
man nicht aus einer Zusammenfassung, sondern indem man Fachleuten beim
Streiten zuhört und dazwischenfragen darf.

Die Diskussionsrunde ist das einzige Format, das **live** antwortet. Alle
anderen sind erzeugte Artefakte (TB-4).

## 1. Die Runde

### DIS-1 — Drei bis vier Standpunkte, nicht drei Namen
Eine Runde besetzt Rollen mit unterschiedlichen fachlichen Perspektiven auf
dasselbe Material, etwa die anwendende, die prüfende und die kritische.

Eine Runde aus drei Zustimmern ist ein Podcast mit mehr Sprechern.

### DIS-2 — Perspektiven kommen aus dem Material
Die Besetzung leitet sich aus den übergebenen Wissenseinheiten ab. Wo BIB-9
einen Widerspruch markiert hat, wird er auf zwei Rollen verteilt.

Damit wird die markierte fachliche Uneinigkeit zum Lerninhalt, statt
weggeglättet zu werden.

### DIS-3 — Jede Rolle bleibt an der Bibliothek
Auch eine zugespitzte Position stützt sich auf Belege. Eine Rolle darf
gewichten und bewerten, aber keine Tatsachen hinzufügen (AUF-3).

### DIS-4 — Die Runde hat einen Moderator
Eine Rolle führt durch das Gespräch, fasst zusammen und nimmt die Fragen des
Lernenden auf.

### DIS-5 — Uneinigkeit wird benannt, nicht aufgelöst
Wo die Bibliothek keinen Schiedsspruch hergibt, sagt der Moderator das und
lässt die Positionen stehen.

## 2. Rückfragen

### DIS-6 — Der Lernende darf jederzeit fragen
Das System nimmt zu jedem Zeitpunkt eine Frage entgegen und beantwortet sie
aus den Wissenseinheiten der laufenden Runde.

### DIS-7 — Antwort mit Beleg
Jede Antwort auf eine Rückfrage nennt den Beleg, auf dem sie steht.

### DIS-8 — Die ehrliche Absage
Wenn eine Rückfrage aus der Bibliothek nicht beantwortbar ist, sagt das
System das ausdrücklich und bietet an, die Frage als Rechercheauftrag
aufzunehmen (BIB-14).

Das ist der Punkt, an dem TeachBuddy sich von einem Chatbot unterscheidet,
und der Punkt, an dem es am meisten kostet, ehrlich zu bleiben: Ein Modell
kann fast jede Frage plausibel beantworten. Genau das soll es hier nicht
(TB-8).

### DIS-9 — Aus Lücken wird Bibliothek
Eine so aufgenommene Frage erscheint als offener Rechercheauftrag. Wird er
bearbeitet, wächst die Bibliothek an der Stelle, an der der Lernende
tatsächlich angestoßen ist.

Das ist der Rückkanal des ganzen Systems: Die Lücken zeigt der Lernende,
nicht der Kurator.

### DIS-10 — Gespräche bleiben erhalten
Eine Runde samt Rückfragen und Antworten wird gespeichert und ist später
wieder lesbar.

## 3. Betrieb

### DIS-11 — Live heißt Sekunden bis Minuten
Eine Rückfrage wird über die Abo-CLI beantwortet (TB-5, AUF-4). Die App
zeigt an, dass gearbeitet wird, statt eine Antwortzeit zu versprechen.

### DIS-12 — Eine Runde zur Zeit
Das System führt nicht mehrere Diskussionsrunden gleichzeitig (AUF-10).

### DIS-13 — Grenze erreicht ist eine Aussage
Wenn der Abo-Zugang seine Nutzungsgrenze meldet, sagt das System das im
Klartext und nennt, wann es wieder geht.

„Es hat gerade nicht geklappt" bei einem Rate Limit schickt den Nutzer auf
Fehlersuche an der falschen Stelle.

## 4. Form

> **OFFEN (E-13):** Wird die Runde als **Text** geführt (Chatverlauf mit
> Sprechernamen) oder wie der Podcast **vertont**? Text ist der einfachere
> Start, erlaubt Rückfragen ohne Bruch und ist durchsuchbar. Vertonung wäre
> ein zweiter Schritt und würde bei jeder Rückfrage eine Vertonung
> brauchen, die Geld kostet (POD-7a). Empfehlung: Text zuerst.

## 5. Führung ohne Gängelung

### Problem

Eine Agenda im Systemprompt hält nicht. Das Modell sieht die Liste, hat aber
keinen Zustand darüber, was erledigt ist — es erinnert sich, und Erinnerung
verblasst hinter zwanzig Gesprächsminuten. Ergebnis: Punkte werden zu früh
abgehakt, gestreift statt geprüft, oder ganz vergessen.

Die Tutoring-Forschung sagt dasselbe: Wer nur die Modellschicht ausliefert,
bekommt ein unterhaltsames Gespräch ohne Lernwirkung. Es braucht ein
Lernermodell und einen Zustand außerhalb des Modells.

Zugleich darf das Gegenmittel nicht zur Gängelung werden. Ein Moderator, der
eine Liste abarbeitet, führt ein Verhör.

### DIS-14 — Die Agenda ist eine Landkarte, kein Drehbuch
Ein Kapitelgespräch hat **Punkte, die berührt werden sollen**, aber **keine
Reihenfolge**. Der Partner wählt selbst, wann er welchen anspricht und wie er
dorthin kommt.

Eine Reihenfolge wäre das Ende des Gesprächs: Sie zwingt ihn, den Lernenden
zurückzuholen, wenn der gerade etwas Interessantes verfolgt.

### DIS-15 — Der Zustand liegt außerhalb des Modells
Welche Punkte berührt und welche geprüft sind, hält der Server (Sideband-
Verbindung), nicht das Modell.

### DIS-16 — Abhaken ist eine Handlung, keine Notiz
Der Partner hat ein Werkzeug, mit dem er einen Punkt als geprüft meldet:

```
punkt_geprueft(id, urteil, begruendung)
   urteil:      sitzt | halb | sitzt_nicht
   begruendung: woran er das festmacht — was der Lernende gesagt hat
```

Der Zwang zur Handlung ist der Kern. Eine Notiz im Fließtext verschwindet im
Verlauf; ein Werkzeugaufruf ist ein Ereignis, das der Server sieht und speichert.

### DIS-17 — Geprüft heißt gezeigt, nicht erwähnt
Ein Punkt gilt erst als geprüft, wenn der **Lernende** ihn gezeigt hat. Dass
der Partner ihn erklärt hat, ist kein Nachweis.

Das ist die Regel, an der Gefälligkeit scheitert. Ein Modell hakt gern ab,
sobald ein Thema vorkam. Die `begruendung` zwingt es, sich auf eine Äußerung
des Lernenden zu berufen.

### DIS-18 — Der Server frischt auf, statt zu drängeln
Der Server schickt eine aktualisierte Instruktion (`session.update`), wenn einer
dieser Fälle eintritt:

- **Ein Punkt wurde mehrfach gestreift, aber nie geprüft.**
- **Längere Zeit ohne Berührung eines offenen Punktes.**
- **Die verabredete Gesprächsdauer nähert sich dem Ende** und offene Punkte
  bleiben.
- **Ein Punkt wurde als `sitzt_nicht` gemeldet** und ist seither nicht wieder
  aufgegriffen worden.

Die Instruktion nennt die offenen Punkte neu und rückt sie damit wieder nach
vorn. Sie sagt **nicht**, was als Nächstes zu fragen ist.

### DIS-19 — Eingriffe sind selten und unsichtbar
Der Server greift nicht bei jedem Sprecherwechsel ein. Der Lernende merkt nichts
davon.

Ein Moderator, der alle zwei Minuten auf seine Liste sieht, ist kein
Gesprächspartner mehr.

### DIS-20 — Abtauchen ist erlaubt und wird verzeichnet
Verfolgt der Lernende einen Nebenstrang, ist das kein Fehler. Der Partner
folgt ihm.

Führt der Nebenstrang über die Bibliothek hinaus, wird er nach DIS-8 und
DIS-9 behandelt: gekennzeichnet und als Rechercheauftrag aufnehmbar. **Ein
Abtauchen ist damit kein Verlust, sondern der Rückkanal**, an dem die
Bibliothek wächst.

### DIS-21 — Drei Gangarten
Der Partner passt seine Führung dem Zustand an:

| Lage | Verhalten |
|---|---|
| viel Zeit, viele offene Punkte | er führt, bringt Punkte aktiv ein |
| Lernender taucht ab, Zeit reicht | er folgt und lässt laufen |
| Zeit wird knapp, Punkte offen | er wird direkter und sagt das auch |

Der letzte Fall gehört ausgesprochen: „Wir haben noch zehn Minuten, und drei
Dinge sind offen — welches willst du?" Das ist ehrlicher als unauffälliges
Steuern und gibt dem Lernenden die Wahl (TB-8).

### DIS-22 — Am Ende steht eine Bilanz
Zum Schluss zeigt das System, welche Punkte saßen, welche halb, welche nicht,
und welche gar nicht berührt wurden.

Daraus speist sich der Lernstand in der Mindmap (MMP-7) und die Auswahl
späterer Prüfungsfragen (PRF-12).

### DIS-23 — Die Agenda kommt aus dem Kapitel
Die Punkte werden aus den Wissenseinheiten des Kapitels erzeugt, nicht von
Hand geschrieben. Eine Wissenseinheit, die niemand im Gespräch prüfen kann,
ist ein Hinweis auf eine schlecht geschnittene Einheit.

> **OFFEN (E-23):** Wie viele Punkte ein Gespräch trägt. Zu viele machen es
> zur Abfrage, zu wenige lassen es zerfasern. Vermutung: fünf bis acht bei
> zwanzig Minuten. Am ersten echten Gespräch zu messen.

## 6. Die Werkzeuge des Sprachpartners

### DIS-24 — Der Partner ruft, der Server antwortet
Werkzeugaufrufe gehen **vom Modell aus**. Es entscheidet im Gespräch, wann es
abhakt, nachschlägt oder recherchiert — so wie es entscheidet, was es sagt.
Der Server beantwortet die Aufrufe über die Sideband-Verbindung und hält den
Zustand; er löst nichts aus.

Ohne eigene Werkzeuge bliebe der Sprachkanal dumm: ein Modell mit einem
Kontextfenster und sonst nichts. Mit ihnen ist er ein Agent, der dieselbe
Bibliothek befragen kann wie jede andere Rolle.

### DIS-25 — Vier Werkzeuge

| Werkzeug | wofür | Dauer |
|---|---|---|
| `punkt_geprueft(id, urteil, begruendung)` | Agenda-Zustand (DIS-16) | sofort |
| `bibliothek_nachschlagen(frage)` | in der **ganzen** Bibliothek suchen, nicht nur im Kapitelkontext | Millisekunden |
| `recherchieren(frage)` | Websuche, wenn die Bibliothek nichts hergibt | Sekunden bis Minuten |
| `rechercheauftrag_aufnehmen(frage, zusammenhang)` | Lücke für später festhalten (DIS-9) | sofort |

### DIS-26 — Nachschlagen geht über das Kapitel hinaus
`bibliothek_nachschlagen` durchsucht die gesamte Bibliothek über den
Volltextindex (BIB-18b), nicht nur die Wissenseinheiten des laufenden
Kapitels.

Der Kapitelkontext steckt im Sitzungsprompt (OBF-14) und deckt ab, worüber
geredet wird. Fragt der Lernende nach etwas aus einem anderen Kapitel, soll
der Partner es **belegt** beantworten können, statt zu sagen, das gehöre
nicht hierher. Genau dafür wurde der Index gebaut.

### DIS-27 — Der Partner kennt das Tempo seiner Werkzeuge
Er weiß, welcher Aufruf sofort zurückkommt und welcher dauert, und richtet
seine Sprache danach:

- **Sofort und stumm:** Abhaken und Aufträge aufnehmen. Kein Wort darüber.
  „Ich notiere das kurz" mitten im Gespräch ist Buchhaltung, kein Gespräch.
- **Kurz und beiläufig:** Nachschlagen. Eine halbe Sekunde ist kein Anlass
  für eine Ankündigung.
- **Angekündigt:** Recherchieren. Hier sagt er, dass er nachsieht, und
  überbrückt die Wartezeit — am besten mit einer Rückfrage, die der Lernende
  währenddessen beantworten kann.

Asynchrone Werkzeugaufrufe unterbrechen die Sitzung nicht; der Partner kann
weiterreden, während der Server arbeitet. Ein Gespräch, das für zwanzig Sekunden
verstummt, ist trotzdem kaputt — die Überbrückung ist seine Aufgabe, nicht
die der Technik.

### DIS-28 — Recherchiertes ist kein Beleg
Was `recherchieren` zurückgibt, ist **ungeprüft**. Es hat keinen
Rechercheur-Lauf, keine Gegenprüfung und keine Freigabe durchlaufen (BIB-16).

Der Partner kennzeichnet es im Gespräch als **frisch nachgesehen, nicht aus
der Bibliothek** (OBF-17), und es landet im Eingang, nicht in der Bibliothek.

Das ist die Stelle, an der TB-1 unter Druck gerät: Eine Live-Antwort fühlt
sich genauso verlässlich an wie eine belegte, weil beide aus demselben Mund
kommen. Nur die Kennzeichnung hält sie auseinander.

### DIS-29 — V1: Kennzeichnung genügt, Auftrag ist freiwillig
**Für den ersten Bau (11.09.2026):** Die Kennzeichnung im Gespräch
reicht. Live Recherchiertes wird als solches ausgewiesen (DIS-28) und im
Verlauf festgehalten (DIS-30); ob daraus ein Rechercheauftrag wird,
entscheidet der Lernende mit einem Griff (DIS-9).

Kein Automatismus. Erst messen, wie oft der Fall überhaupt eintritt.

**Nachtrag 14.09.2026, beim Bau.** DIS-25 gibt dem Partner
`rechercheauftrag_aufnehmen` an die Hand, DIS-29 wollte die Entscheidung beim
Lernenden. Das ist ein Widerspruch in der Spec, und er wird zugunsten von
DIS-25 aufgelöst:

Der Partner nimmt den Auftrag auf, wenn ihm im Gespräch eine Lücke auffällt.
Das ist **kein Automatismus** — keine Regel löst es aus, er urteilt. Und es
ist folgenlos: Ein Auftrag steht unter `/api/recherchen?auftraege=1`, nichts
davon gelangt in die Bibliothek, niemand muss ihn abarbeiten. Die Alternative
wäre, dass die Lücke im Gespräch verklingt — und genau das ist der Verlust,
gegen den OBF-18 geschrieben wurde.

Gezählt wird trotzdem: `/api/kosten` führt die Recherche-Aufrufe. Die Frage
„wie oft tritt der Fall ein" bleibt damit beantwortbar.

**Der Kipp-Punkt, ab dem es einen braucht:** Sobald live Nachgesehenes
regelmäßig vorkommt, entsteht eine zweite, ungeprüfte Wissensschicht neben
der Bibliothek — Dinge, die im Gespräch gesagt und nie belegt wurden und
trotzdem hängen bleiben. Das ist der schleichende Weg zurück zum Chatbot, und
zwar der, den man nicht bemerkt.

**Woran man es sieht:** Der Verlauf hält jeden `recherchieren`-Aufruf fest.
Wenn in mehreren Gesprächen hintereinander live nachgesehen wurde, ist das
kein Einzelfall mehr, sondern eine Lücke in der Bibliothek — und dann wird
der Auftrag Pflicht.

### DIS-30 — Werkzeugaufrufe stehen im Verlauf
Der gespeicherte Gesprächsverlauf (DIS-10) enthält, welche Werkzeuge wann mit
welchem Ergebnis gerufen wurden.

Ohne diese Spur lässt sich später nicht mehr sagen, ob eine Aussage aus der
Bibliothek kam, live nachgesehen oder aus dem Gedächtnis des Modells stammt —
und das ist genau die Unterscheidung, um die es geht.

### DIS-31 — Der Verlauf kommt aus dem Browser, nicht vom Server
Der Ton läuft direkt vom Browser zum Anbieter (E-20a). Der Server hört nicht mit
und kann den Verlauf nicht selbst mitschreiben.

Die Mitschrift meldet deshalb **der Browser**, in Schüben während der Sitzung
und einmal beim Schließen. Bleibt sie aus, ist der Verlauf leer — und die App
sagt das, statt die Lücke zu füllen: Ob nichts gesprochen wurde oder die
Meldung ausblieb, ist vom Server aus nicht zu unterscheiden.

Daraus folgt für den Anbieter, dass die **Abschrift der Nutzerrede
eingeschaltet** sein muss. Ohne sie kommt nur die eigene Rede des Partners
zurück, und das Gedächtnis wäre einseitig.

### DIS-32 — Der Partner erinnert sich über Sitzungen hinweg
Beim Start einer Sitzung bekommt der Partner, was in den **letzten drei
Sitzungen zu diesem Kapitel** gesprochen wurde.

Ohne das ist jedes Gespräch das erste. Der Partner fragt wieder, was schon
saß, und der Lernende trägt die Fortsetzung allein.

Drei Sitzungen und nicht alle: Ein Sitzungsprompt, der jedes je gesprochene
Wort mitschleppt, wächst mit jeder Sitzung, wird teurer und verliert am Ende
den Bezug zum aktuellen Stand.

**Der Partner tut nicht so, als erinnerte er sich an mehr.** Was ihm vorliegt,
ist die Mitschrift, nicht ein Gedächtnis — und auf die Frage, worüber
gesprochen wurde, antwortet er aus ihr (TB-8).
