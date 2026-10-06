# App und Auslieferung — Spec     (ID-Präfix: APP)

> Status: Entwurf · trägt TB-4, TB-5, TB-6

## Problem

Die Artefakte liegen auf dem Server. Gelernt wird unterwegs: im Zug, beim Laufen,
auf dem Sofa. Die App ist die Brücke, und sie muss auf dem Telefon
funktionieren, auch wenn der Server gerade nicht erreichbar ist.

## 1. Zuschnitt

### APP-1 — Eine PWA, keine Store-App
Die App ist eine Progressive Web App: eine Webseite, die sich auf dem
Telefon installieren lässt.

Kein Store, kein Signaturprozess, kein Entwicklerkonto, eine Codebasis für
Android und iOS. Für ein Werkzeug mit einem Nutzerkreis von wenigen Personen
ist alles andere unverhältnismäßig.

### APP-2 — Der Browser spricht nie mit einem Modell, außer im Sprachkanal
Alle Agentenaufrufe laufen auf dem Server. Die App spricht ausschließlich mit
dem Server.

**Eine Ausnahme: das Sprachgespräch** (E-20a). Echtzeit-Audio über den Server zu
leiten, fügte genau die Latenz hinzu, derentwegen der Server-Weg verworfen wurde.
Dort verbindet sich der Browser direkt mit dem Anbieter.

**Der Schlüssel bleibt auf dem Server.** Die App holt sich vor jeder Sitzung ein
kurzlebiges Token; der langlebige Schlüssel liegt nie im Browser, und der Server
entscheidet bei jeder Anfrage, ob eine Sitzung eröffnet wird.

Das folgt zwingend aus TB-5: Der Abo-Zugang hängt an der CLI auf dem Server und
an die Anmeldung. Es gibt nichts, was ein Browser vorzeigen könnte, und
es wäre auch mit API-Schlüssel falsch, Zugangsdaten in ein Frontend zu legen.

### APP-3 — Drei Navigationsebenen, darin die Formate
Die App navigiert über **Übersicht**, **Kapitel** und **Lektion** (OBF-2a).
Die vier Formate liegen darin, nicht daneben: Podcast mit Handreichung und
Prüfer in der Lektion, Mindmap und Diskussionsrunde im Kapitel.

### APP-4 — Neue Formate ohne App-Umbau
Ein fünftes Format soll eine neue Ansicht kosten und keine Änderung an
Navigation, Datenmodell oder Auslieferung (TB-3).

## 2. Offline

### APP-5 — Heruntergeladenes bleibt verfügbar
Ein Podcast samt Handreichung, ein Fragenvorrat und eine Mindmap sind nach
einmaligem Laden ohne Verbindung nutzbar.

Das ist der Hauptgrund für die PWA statt einer Webseite. Im Zug ist der Server
nicht erreichbar, und genau dort wird gehört.

### APP-6 — Die Diskussionsrunde ist ehrlich offline
Ohne Verbindung zeigt die App vergangene Runden (DIS-10), nimmt aber keine
neuen Rückfragen an und sagt warum.

Rückfragen brauchen den Server (DIS-11). Eine Frage anzunehmen und ins Leere
laufen zu lassen, wäre schlimmer als sie abzulehnen.

### APP-7 — Prüfungsergebnisse werden nachgereicht
Offline gegebene Antworten werden gespeichert und übertragen, sobald die
Verbindung steht.

> **OFFEN (E-17):** Offline bewerten geht nicht, die Bewertung braucht ein
> Modell (PRF-7). Der Lernende bekommt seine Rückmeldung also verzögert.
> Alternative wäre, offline nur die Musterantwort zum Selbstvergleich zu
> zeigen. Das ist schwächer, aber sofort. Vermutlich wollen wir beides.

## 3. Erreichbarkeit

### APP-8 — Standardmäßig lokal, im Netz nur mit Zugangscode
Die App lauscht ohne weitere Angabe nur auf `127.0.0.1`. Wer sie im Netz
erreichbar macht (`TEACHBUDDY_APP_HOST`), setzt einen Zugangscode
(`TEACHBUDDY_ZUGANGSCODE`): Ein Gerät öffnet die Adresse einmal mit
`?zugang=<code>` und bekommt ein Cookie.

Der Grund ist nicht der Lernstand, sondern das Geld: Hinter der App liegen
Wege, die pro Minute oder pro Zeichen abgerechnet werden (Gespräch,
Vertonung). Der Preis ist benannt: Ein cookie-gesicherter öffentlicher
Endpunkt ist schwächer als ein privates Netz (VPN), in das man erst
hineinkommen muss. Wer den Link samt gültigem Cookie hat, ist drin.

### APP-8a — Was hinter dem Cookie liegt, ist der Lernstand, nicht die Bibliothek
Die App liefert Lektionen, Folien, Fragen und den Fortschritt aus. Sie stellt
**keinen** Endpunkt bereit, über den sich die Bibliothek als Ganzes abrufen
oder ändern lässt.

Die Bibliothek liegt in Git auf dem Server und wird dort gepflegt (E-9). Das
begrenzt den Schaden eines abhandengekommenen Cookies auf das, was ohnehin
zum Anhören gedacht war.

### APP-9 — HTTPS ist Voraussetzung, nicht Kür
Die App wird über HTTPS mit gültigem Zertifikat ausgeliefert.

Das ist keine Vorsichtsmaßnahme, sondern eine harte technische Bedingung:
**Ohne HTTPS gibt es keinen Service Worker, und ohne Service Worker gibt es
kein Offline und keine Installation** (APP-1, APP-5). Über `http://` auf
einem anderen Namen als `localhost` wäre TeachBuddy nur eine Webseite.

Den Weg liefert ein Reverse-Proxy mit Zertifikat davor — etwa Caddy, nginx
mit Let's Encrypt oder `tailscale serve`.

### APP-10 — Ein Dienst, sparsam
TeachBuddy läuft als ein Dienst plus ein kleiner Auslieferer, auch auf
kleiner Hardware (TB-6).

Auf einer Maschine, deren Engpass Arbeitsspeicher ist, ist jeder zusätzliche
Dauerprozess eine Entscheidung. Erzeugungsaufträge laufen einzeln und geben ihren Speicher danach
wieder frei (AUF-10).

### APP-11 — Zwischendateien unter `arbeit/`
Zwischenergebnisse der Erzeugung, besonders Audiosegmente, landen unter
`arbeit/` (siehe `pfade.py`), nicht im System-Temp.

Auf kleinen Geräten ist `/tmp` oft ein RAM-Dateisystem. Podcast-Segmente
füllen es schnell, und dann trifft es andere Dienste auf derselben Maschine.

## 4. Der Chat in der App

### APP-12 — Der Chat ist immer an ein Kapitel gebunden
Es gibt keinen allgemeinen Chatbot neben den Formaten. Jedes Gespräch gehört
zu einem Kapitel und startet mit dessen Wissenseinheiten als Kontext
(OBF-13, OBF-14).

Ein freier Chat ohne Kapitelbindung wäre die Umgehung der ganzen Bibliothek:
Er beantwortet dieselben Fragen unbelegt und bequemer, und danach nimmt
niemand mehr den belegten Weg. Damit fiele TB-1.

Innerhalb eines Kapitels darf der Diskussionspartner über die Bibliothek
hinausgehen, aber nur gekennzeichnet (OBF-17) und mit dem Rückkanal in die
Recherche (OBF-18).

> **OFFEN (E-20):** Ob das Gespräch als eingebettetes ChatGPT-Widget läuft
> (nutzt das Pro-Abo unmittelbar, hat aber keinen Zugriff auf den Server, außer
> über eine öffentlich erreichbare Schnittstelle) oder über den Server mit
> `codex exec` im Hintergrund (voller Zugriff auf Bibliothek und Lernstand,
> dafür Antwortzeiten in Sekunden bis Minuten). Die Widget-Variante wurde
> vorrecherchiert. Diese Frage entscheidet Abschnitt 4 der Oberflächen-Spec
> und sollte vor dem ersten Frontend-Lauf fallen.

### APP-13 — Kein Modellzugang im Browser, außer im Widget-Fall
Läuft das Gespräch über den Server, nimmt der Dienst die Frage entgegen, ruft die
Abo-CLI und liefert die Antwort zurück (APP-2).

Läuft es als eingebettetes Widget, spricht der Browser mit dem Anbieter, und
APP-2 gilt für diesen einen Fall nicht. Dann gilt stattdessen: Der Kontext
des Kapitels wird beim Start übergeben, und es gibt keinen Weg vom Widget
zurück in die Bibliothek, der nicht ausdrücklich in APP-8a erlaubt ist.

> **OFFEN (E-4):** Ob die Antwort schrittweise beim Tippen erscheint
> (Streaming) oder als Block. Betrifft nur den Server-Weg; ein Widget streamt
> ohnehin.

## 5. Technik

### APP-14 — Die PWA entsteht ohne Framework und ohne Build-Schritt
ES-Module im Browser, Web Components wo ein Ding Zustand hat, CSS Custom
Properties als Marken, `sw.js` von Hand. Fremde Bibliotheken liegen als fertige
ESM-Dateien im Repo, nicht hinter einem CDN (E-5).

Der Grund ist APP-9: Ohne Build cacht der Service Worker genau die Dateien, die
der Dienst ausliefert. Mit einem Bündler heißen sie nach jedem Bau anders, und
es braucht ein zweites Werkzeug, das die Liste pflegt — genau dort entstehen
Offline-Fehler.

### APP-15 — Ein Dienst in Python, mit Flask
Der Dienst ist Python und nutzt Flask (E-1). Er liefert
die statischen Dateien der PWA und die API aus demselben Prozess (APP-10).

Damit bleibt das Provider-Muster aus `hoerspiel/providers/base.py` nutzbar
(TB-7), und im Haus gibt es weiterhin genau eine Sprache und einen Web-Rahmen.
