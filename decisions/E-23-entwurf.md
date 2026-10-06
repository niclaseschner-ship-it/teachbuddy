# Führung des Sprachpartners — Architektur

**Entwurf, 11.09.2026.** Antwort auf: „Wir müssen die Diskussionspartner aktiv
guiden und eine Art Checkliste mitgeben, das geht nicht nur über Prompt."

## Die Lage

Ein Systemprompt ist **kein Zustand**. Das Modell sieht die Agenda, weiß aber
nicht, was erledigt ist — es erinnert sich, und die Erinnerung verblasst im
Verlauf. Deshalb hakt es zu früh ab oder verliert Punkte.

Das deckt sich mit der Tutoring-Forschung: Wer nur die Modellschicht
ausliefert, bekommt Beteiligung ohne Lernwirkung. Es braucht Lernermodell,
Curriculum-Graph und einen Zustand außerhalb des Modells.

## Der Aufbau

Die Realtime-API erlaubt **zwei Verbindungen zur selben Sitzung**: eine vom
Browser für das Audio, eine vom Server (Sideband).

```
Browser ──WebRTC, nur Audio──►  Realtime-Sitzung
                                      ▲
Server ─────Sideband──────────────────────┘
        · beobachtet Ereignisse
        · hält den Agenda-Zustand
        · beantwortet Werkzeugaufrufe
        · schickt session.update, wenn nötig
```

Drei Eigenschaften machen das tragfähig:

1. **`session.update` gilt jederzeit**, für jedes Feld außer Stimme und
   Modell — auch für `instructions`. Der Server kann die Agenda also mitten im
   Gespräch neu nach vorn rücken, wenn sie verblasst.
2. **Werkzeugaufrufe laufen serverseitig.** Die Logik liegt nicht im Browser.
3. **Asynchrone Werkzeugaufrufe blockieren nicht.** Das Modell redet weiter,
   während der Server antwortet — für ein Gespräch entscheidend.

## Die zwei Hälften

### Zustand: Abhaken als Handlung
Der Partner bekommt ein Werkzeug `punkt_geprueft(id, urteil, begruendung)`.
Ein Werkzeugaufruf ist ein Ereignis, das der Server sieht und speichert; eine
Notiz im Fließtext verschwindet.

Die `begruendung` ist der eigentliche Trick: Sie zwingt zur Berufung auf eine
Äußerung des **Lernenden**. Damit scheitert Gefälligkeit — ein Modell hakt
gern ab, sobald ein Thema vorkam (DIS-17).

### Freiheit: Landkarte statt Drehbuch
Die Agenda hat **keine Reihenfolge**. Der Server greift nur in vier Fällen ein
(DIS-18), der Lernende merkt nichts davon (DIS-19), und Abtauchen ist
ausdrücklich erlaubt und wird zum Rückkanal in die Recherche (DIS-20).

Der Moderator hat drei Gangarten je nach Zeit und offenen Punkten (DIS-21),
und in der engsten sagt er es offen: „Wir haben noch zehn Minuten, drei Dinge
sind offen — welches willst du?"

## Der Partner ruft selbst, und nicht nur zum Abhaken

Präzisierung nach einem Einwand: **Werkzeugaufrufe gehen vom Modell aus.** Der
Server beantwortet sie, er löst sie nicht aus. Sonst bliebe der Sprachkanal ein
Modell mit Kontextfenster und sonst nichts.

Daraus folgt, dass Abhaken nicht das einzige Werkzeug sein sollte. Der
Partner bekommt vier (DIS-25): Agenda abhaken, in der **ganzen** Bibliothek
nachschlagen, live recherchieren, Rechercheauftrag aufnehmen.

`bibliothek_nachschlagen` ist dabei der unterschätzte Gewinn: Der
Kapitelkontext im Sitzungsprompt deckt ab, worüber geredet wird, aber fragt
der Lernende nach etwas aus einem anderen Kapitel, kann der Partner es
**belegt** beantworten statt abzuwinken. Genau dafür wurde der Volltextindex
aus E-9 gebaut.

Der Preis steht in DIS-28 und DIS-29: Live Recherchiertes ist **kein Beleg**,
wird als solches gekennzeichnet und wird **immer** zu einem Rechercheauftrag.
Sonst entsteht eine zweite, ungeprüfte Wissensschicht neben der Bibliothek,
und das wäre der schleichende Weg zurück zum Chatbot.

## Was daran schwierig bleibt

**Gefälligkeit.** Das Modell wird trotzdem zu früh abhaken wollen. Die
`begruendung` macht es überprüfbar, aber nicht unmöglich. Falls es auffällt:
ein zweites, billiges Modell prüft die Begründungen nach — ein Fall für die
Cross-Model-Probe aus AUF-15.

**Zu viele Eingriffe machen es starr.** Die vier Auslöser in DIS-18 sind eine
begründete Vermutung, keine Messung. Sie gehören am ersten echten Gespräch
nachjustiert.

**Wie viele Punkte ein Gespräch trägt**, ist offen (E-23). Vermutung: fünf
bis acht bei zwanzig Minuten.

## Quellen

- [Realtime conversations — OpenAI](https://developers.openai.com/api/docs/guides/realtime-conversations)
- [Developer notes on the Realtime API (Sideband-Muster)](https://developers.openai.com/blog/realtime-api)
- [Exploring Knowledge Tracing in Tutor-Student Dialogues using LLMs](https://arxiv.org/abs/2409.16490)
- [Intelligent Tutoring Systems: The 2026 Playbook](https://www.forasoft.com/blog/article/intelligent-tutoring-systems-educators)
