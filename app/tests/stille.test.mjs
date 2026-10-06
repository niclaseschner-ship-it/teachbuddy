// Prueft die Stille-Erkennung des Sprachgespraechs.
//
// Zweimal hat dieselbe Stelle die Sitzung mitten im Satz geschlossen: einmal,
// weil der AudioContext auf Android `suspended` startet und der Analyser dann
// nur Nullen liefert, einmal, weil nur das Mikrofon gemessen wurde und nicht
// die Stimme des Partners. Beide Faelle stehen hier.

import assert from 'node:assert/strict';
import test from 'node:test';

/** Ein AudioContext-Ersatz, dessen Analyser einen waehlbaren Pegel liefert. */
function stelleKontext({ zustand = 'running', pegel = () => 0 } = {}) {
  globalThis.window = {
    AudioContext: class {
      constructor() { this.state = zustand; }
      resume() { this.state = 'running'; return Promise.resolve(); }
      close() { return Promise.resolve(); }
      createAnalyser() {
        return {
          fftSize: 512,
          frequencyBinCount: 256,
          getByteTimeDomainData(puffer) {
            const p = this.state === 'suspended' ? 0 : pegel();
            puffer.fill(128 + p);
          },
          state: zustand,
        };
      }
      createMediaStreamSource() { return { connect() {} }; }
    },
  };
}

// `visibilitychange` braucht ein document. Mehr als diese zwei Felder fasst
// der Code davon nicht an.
globalThis.document = {
  visibilityState: 'visible',
  addEventListener() {},
  removeEventListener() {},
};

const { Gespraech, STILLE_SEK, HINTERGRUND_SEK } = await import('../gespraech.js');

const bau = () => {
  const g = new Gespraech('K-01');
  g.strom = { getAudioTracks: () => [{}], getTracks: () => [] };
  return g;
};

test('ein schlafender Kontext schaltet die Sitzung nicht ab', () => {
  stelleKontext({ zustand: 'suspended', pegel: () => 0 });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g.stilleAb = Date.now() - (STILLE_SEK + 60) * 1000;   // laengst „still“
  let zu = false;
  g.beenden = () => { zu = true; };
  g._takt();
  assert.equal(zu, false, 'ohne gemessenen Ton darf nicht abgeschaltet werden');
});

test('gemessener Ton haelt die Sitzung offen', () => {
  stelleKontext({ pegel: () => 30 });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g.stilleAb = Date.now() - (STILLE_SEK + 60) * 1000;
  let zu = false;
  g.beenden = () => { zu = true; };
  g._takt();
  assert.equal(zu, false);
  assert.ok(Date.now() - g.stilleAb < 1000, 'Sprechen setzt die Stilleuhr zurueck');
});

test('echte Stille schliesst, sobald je gemessen wurde', () => {
  let laut = 30;
  stelleKontext({ pegel: () => laut });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g._takt();                       // einmal Ton: die Messung funktioniert
  laut = 0;
  g.stilleAb = Date.now() - (STILLE_SEK + 1) * 1000;
  let grund = null;
  g.beenden = (x) => { grund = x; };
  g._takt();
  assert.equal(grund, 'stille');
});

test('der Partner zaehlt gegen die Stille, nicht nur das Mikrofon', () => {
  stelleKontext({ pegel: () => 30 });
  const g = bau();
  g.strom = null;                             // Mikrofon stumm/aus
  g._stilleBeobachten({ id: 'partner' });     // nur der eingehende Strom
  g.begonnen = Date.now();
  g.stilleAb = Date.now() - (STILLE_SEK + 60) * 1000;
  let zu = false;
  g.beenden = () => { zu = true; };
  g._takt();
  assert.equal(zu, false, 'waehrend der Partner spricht ist es nicht still');
});

// --- Sperrbildschirm (14.09.2026) ----------------------------------------
//
// Rückmeldung: „aufgehängt, vielleicht weil das Handy in den Sperrbildschirm ist?"
// Er hatte recht. Beim Sperren hält der Browser den AudioContext an, der
// Messer liest Nullen, das zählte als Stille — nach fünfzehn Sekunden war die
// Sitzung zu, und beim Entsperren einfach weg.
//
// **Stille und ein abgeschaltetes Mikrofon sind nicht dasselbe.** Das eine
// heißt „er denkt nach", das andere „wir wissen es nicht".

test('eine verdeckte Seite wird nicht wegen Stille geschlossen', () => {
  stelleKontext({ zustand: 'suspended', pegel: () => 0 });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g._jeGemessen = true;                       // vorher lief die Messung
  const langeStill = Date.now() - (STILLE_SEK + 60) * 1000;
  g.stilleAb = langeStill;
  g.verstecktAb = Date.now() - 5 * 1000;      // seit fuenf Sekunden verdeckt
  let grund = null;
  g.beenden = (x) => { grund = x; };
  g._takt();
  assert.equal(grund, null, 'Bildschirm aus ist keine Stille');
  // `stilleAb` bleibt stehen — es ist der Merker „zuletzt etwas gehoert“ und
  // damit genau das Signal, an dem taub von still zu unterscheiden ist.
  assert.equal(g.stilleAb, langeStill, 'der Merker wird nicht ueberschrieben');
});

test('lange verdeckt und taub: ehrlich beenden, nicht haengen', () => {
  stelleKontext({ zustand: 'suspended', pegel: () => 0 });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g._jeGemessen = true;
  g.verstecktAb = Date.now() - (HINTERGRUND_SEK + 1) * 1000;
  let grund = null;
  g.beenden = (x) => { grund = x; };
  g._takt();
  assert.equal(grund, 'hintergrund', 'mit eigenem Grund, damit die App es sagen kann');
});

test('verdeckt, aber es wird weiter gemessen: das Telefon am Ohr zaehlt', () => {
  // Manche Browser lassen ein laufendes Gespraech mit ausgeschaltetem
  // Bildschirm weiterlaufen. Dann ist nichts kaputt und nichts zu schliessen.
  stelleKontext({ pegel: () => 30 });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g._takt();                                   // Messung laeuft
  g.verstecktAb = Date.now() - (HINTERGRUND_SEK + 30) * 1000;
  let grund = null;
  g.beenden = (x) => { grund = x; };
  g._takt();
  assert.equal(grund, null, 'wer noch hoert, wird nicht abgeschaltet');
});

test('ein laufendes Werkzeug haelt die Sitzung offen', () => {
  // Wer wartet, ist nicht still. Sonst schliesst die Sitzung genau dann, wenn
  // sie am nuetzlichsten ist (14.09.2026).
  let laut = 30;
  stelleKontext({ pegel: () => laut });
  const g = bau();
  g._stilleBeobachten();
  g.begonnen = Date.now();
  g._takt();
  laut = 0;
  g._werkzeugeOffen = 1;
  g.stilleAb = Date.now() - (STILLE_SEK + 1) * 1000;
  let grund = null;
  g.beenden = (x) => { grund = x; };
  g._takt();
  assert.equal(grund, null);
  g._werkzeugeOffen = 0;
  g._takt();
  assert.equal(grund, 'stille', 'danach gilt die Stille wieder');
});

// --- Wake Lock (14.09.2026) ----------------------------------------------
//
// Rückmeldung, nachdem das Verhalten nach dem Sperren schon ehrlich war: „Handy geht
// immer noch aus." Das war die Wurzel, nicht der Sperrbildschirm: Wer spricht,
// fasst das Telefon nicht an, also greift die Bildschirmabschaltung mitten im
// Gespräch. Alles Weitere ist nur Schadensbegrenzung.

test('ohne wakeLock wird es gesagt, nicht verschwiegen', async () => {
  delete globalThis.navigator;
  globalThis.navigator = {};
  const g = bau();
  const gemeldet = [];
  g.addEventListener('wach', (e) => gemeldet.push(e.detail));
  await g._wachHalten();
  assert.equal(gemeldet.length, 1);
  assert.equal(gemeldet[0].moeglich, false,
               'der Mensch muss die Sperre selbst hochsetzen koennen');
  assert.equal(g._wach, undefined, 'ohne Lock kein Lock');
});

test('mit wakeLock wird er gehalten und wieder abgegeben', async () => {
  let freigegeben = false;
  globalThis.navigator = {
    wakeLock: {
      request: async () => ({
        addEventListener() {},
        release: async () => { freigegeben = true; },
      }),
    },
  };
  const g = bau();
  await g._wachHalten();
  assert.ok(g._wach, 'gehalten');

  // Zweimal anfordern gibt keinen zweiten Lock.
  const erster = g._wach;
  await g._wachHalten();
  assert.equal(g._wach, erster);

  g.sitzungId = null;
  await g._beenden(0);
  assert.equal(freigegeben, true, 'am Ende wieder abgeben');
  assert.equal(g._wach, null);
});

test('gibt das Geraet den Lock frei, sagt die Zeile es', async () => {
  // Sonst behauptet sie „Bildschirm bleibt an“, waehrend er laengst weg ist —
  // schlimmer als gar keine Zeile.
  let freigeben = null;
  globalThis.navigator = {
    wakeLock: {
      request: async () => ({
        addEventListener: (art, f) => { if (art === 'release') freigeben = f; },
        release: async () => {},
      }),
    },
  };
  const g = bau();
  g.begonnen = Date.now();
  const gemeldet = [];
  g.addEventListener('wach', (e) => gemeldet.push(e.detail.moeglich));
  await g._wachHalten();
  assert.deepEqual(gemeldet, [true]);

  freigeben();                       // das Geraet nimmt ihn zurueck
  assert.deepEqual(gemeldet, [true, false], 'die Freigabe wird gemeldet');
  assert.equal(g._wach, null, 'damit der naechste Versuch greift');
});
