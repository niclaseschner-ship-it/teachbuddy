// Prueft, dass ein Lektionslink seine Lektion nennt.
//
// Am 13.09.2026 kam die Meldung: „Der naechste Knopf ist in der App, aber
// wenn ich ihn druecke springt er zu einer anderen Folge." Der Knopf zeigte
// einen Titel an und verlinkte `./d-lektion.html` ohne jede Kennung. Die
// Zielseite nimmt ohne `?l=` die erste Lektion, die sie findet — also immer
// dieselbe fremde Folge. Betroffen waren „Weiterhoeren" in der Huelle und
// „vorige"/„naechste" im Abspieler.
//
// Titel sind keine Identitaet.
// Dieser Test ist der Nagel dafuer.

import assert from 'node:assert/strict';
import test from 'node:test';

// `huelle.js` haengt an `daten.js`, und das holt im Modulkopf die Lernpfade
// und greift bei einem Fehler ans `document`. Beides wird hier gestellt, damit
// der Import ueberhaupt gelingt.
globalThis.fetch = async () => ({
  ok: true,
  status: 200,
  json: async () => ({
    lernpfade: [{
      lernpfad: { id: 'P-01', titel: 'Probe', kurzfassung: '—' },
      kapitel: [{
        id: 'K-01', nummer: 1, titel: 'Erstes', lektionen: [
          { id: 'L-A01', titel: 'Eine', dauer_sek: 400, position_sek: 0 },
        ],
      }],
    }],
  }),
});
globalThis.document = { getElementById: () => null, body: {} };

const { lektionsWeg } = await import('../huelle.js');

test('der Weg nennt Kapitel und Lektion', () => {
  const weg = lektionsWeg({ id: 'L-M4' }, { id: 'K-02' });
  assert.equal(weg, './d-lektion.html?k=K-02&l=L-M4');
});

test('ohne eigenes Kapitel zieht er es aus der Lektion', () => {
  // Der Abspieler bekommt Nachbarlektionen, die ihr Kapitel selbst tragen.
  assert.equal(lektionsWeg({ id: 'L-M4', kapitel_id: 'K-02' }),
               './d-lektion.html?k=K-02&l=L-M4');
});

test('das Kapitel allein genuegt nicht — die Lektion muss dastehen', () => {
  // Genau hier lag der Fehler: eine Adresse ohne `l` landet auf der ersten
  // Lektion des ersten Pfads, nicht auf der angezeigten.
  const weg = lektionsWeg({ id: 'L-H3' }, { id: 'K-03' });
  assert.match(weg, /[?&]l=L-H3(&|$)/);
});

test('ein anderes Ziel bleibt erhalten', () => {
  assert.equal(lektionsWeg({ id: 'L-A01' }, { id: 'K-01' }, { ziel: './x.html' }),
               './x.html?k=K-01&l=L-A01');
});

test('ohne jede Angabe kein leeres Fragezeichen', () => {
  assert.equal(lektionsWeg(null, null), './d-lektion.html');
});
