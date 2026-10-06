// sw.js — der Service Worker (APP-5, APP-9).
//
// **Diese Datei ist am 13.09.2026 neu geschrieben worden.** Die alte Fassung
// hat genau die bekannte Runde erzeugt: Die App lief nur noch
// im Privatfenster, war sonst langsam, und niemand wurde den alten Stand
// zuverlässig los.
//
// ## Warum das passiert ist
//
// Ohne Build-Schritt (E-5) heißen alle Dateien nach jedem Lauf gleich. Ein
// Cache, der einzelne Dateien ablegt, kann deshalb eine **alte `daten.js`
// neben einer neuen `uebersicht.html`** ausliefern. Ein ES-Modulimport, der
// ins Leere geht, bricht die Seite ab, bevor irgendetwas gezeichnet ist: kein
// Fehler, keine Zeile, weiß.
//
// „Netzwerk zuerst" hat das nicht gelöst, sondern zwei Probleme gemacht: Es
// genügt, dass **eine** Datei aus dem Cache kommt, während die andere frisch
// ist — und jede Datei einzeln übers Netz zu holen macht die App langsam.
//
// ## Was jetzt gilt
//
// **Der Mantel ist atomar.** Es gibt genau eine Fassung, und sie steht im
// Cache-Namen: `tb-schale-<fassung>`. Die Fassung rechnet der Server aus den
// Dateien auf der Platte (`/version.json`) — nichts zu erzeugen, nichts zu
// pflegen, nichts, das man vergessen kann.
//
// **Geprüft wird beim Seitenaufruf, nicht bei jeder Datei.** Eine Navigation
// holt `version.json` (winzig, nie gecacht). Hat sich die Fassung geändert,
// wird der ganze alte Mantel **gelöscht, bevor die erste Skriptdatei
// angefragt wird**. Danach kann keine Mischung mehr entstehen.
//
// **Dateien kommen aus dem Cache, nicht aus dem Netz.** Innerhalb einer
// Fassung sind sie unveränderlich, also ist das sicher — und schnell.
//
// **Es gibt einen Notausgang:** `neustart.html` wirft Worker und Caches weg.
// Ein Link, der immer funktioniert, ist mehr wert als die Hoffnung, dass es
// diesmal klappt.
//
// Was der Mensch offline gesichert hat, liegt in einem eigenen Cache und
// überlebt jede Fassung. Es gehört ihm, nicht dem Build.

'use strict';

const SCHALE = 'tb-schale-';           // Präfix; dahinter die Fassung
const API = 'tb-api';
const LEKTIONEN = 'tb-lektionen-v1';   // ohne Fassung: gehört dem Menschen

const WURZEL = new URL('./', self.registration.scope).pathname;
const inApp = (weg) => WURZEL + weg;

/**
 * **Kein `skipWaiting()`, kein `clients.claim()`.**
 *
 * Das war die Ursache, nicht die Lösung. Die Dokumentation von Chrome sagt es
 * deutlich: Ein Worker, der sofort übernimmt, tauscht die Dateien unter einer
 * laufenden Seite aus — „your app might crash on the next lazy-loaded chunk
 * request". Bei ES-Modulen heißt das: neue `uebersicht.html`, alte
 * `huelle.js`, und ein Import geht ins Leere.
 *
 * Ich hatte beides drin und habe danach zwei Tage lang eigene Mechanik gebaut,
 * um die Folgen abzufangen. Das Übliche ist einfacher und trägt:
 *
 * * Ein neuer Worker **wartet**, bis keine Seite der alten Fassung mehr offen
 *   ist. Solange bleibt alles konsistent auf dem alten Stand.
 * * Dann übernimmt er, räumt die alten Mäntel weg, und ab da ist alles neu.
 * * Die Seite merkt, dass einer wartet, und sagt es leise (`huelle.js`).
 *
 * **Auf ausdrückliche Bitte darf er trotzdem vorrücken.** Dasselbe Kapitel der
 * Chrome-Dokumentation, das `skipWaiting()` im `install` als Ursache von
 * Versions-Schieflage nennt, empfiehlt als Gegenstück genau das hier: einen
 * Hinweis „neue Fassung — neu laden", und auf Klick übernimmt der wartende
 * Worker. Der Unterschied ist der Zeitpunkt. Im `install` tauscht er die
 * Dateien unter einer **laufenden** Seite aus; hier lädt die Seite unmittelbar
 * danach neu, es gibt also kein Fenster, in dem alte und neue Module
 * nebeneinander leben.
 *
 * Ohne das war der Hinweis eine Lüge: Er rief `location.reload()`, und ein
 * Neuladen hält die Seite am Leben — der Worker wartete weiter. Am 14.09.2026
 * hat das einen ganzen Tag Browser-Reparaturen auf die Telefon aufgehalten,
 * während der Server längst neu war.
 *
 * Eine Seite sieht damit **immer genau eine Fassung** — vom ersten bis zum
 * letzten Modul.
 */
self.addEventListener('message', (e) => {
  // Nur auf ausdrückliche Bitte der Seite, nie von selbst.
  if (e.data && e.data.art === 'jetzt-uebernehmen') self.skipWaiting();
});

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const fassung = await fassungVomServer();
    if (!fassung) return;              // ohne Fassung kein Mantel, dann Netz
    await caches.open(SCHALE + fassung);
  })());
});

self.addEventListener('activate', (e) => {
  // Hier ist es sicher aufzuräumen: Aktiviert wird erst, wenn keine Seite der
  // alten Fassung mehr offen ist.
  e.waitUntil((async () => {
    const meine = await fassungVomServer();
    const namen = await caches.keys();
    await Promise.all(namen
      .filter((n) => (n.startsWith(SCHALE) && n !== SCHALE + meine) || n === API)
      .map((n) => caches.delete(n)));
  })());
});

async function fassungVomServer() {
  try {
    const a = await fetch(inApp('version.json'), { cache: 'no-store' });
    return a.ok ? ((await a.json()).fassung || null) : null;
  } catch {
    return null;
  }
}

/** Der eine Mantel-Cache, der hier liegt. */
async function schale() {
  const namen = await caches.keys();
  const treffer = namen.find((n) => n.startsWith(SCHALE));
  return treffer ? caches.open(treffer) : null;
}

self.addEventListener('fetch', (e) => {
  const anfrage = e.request;
  if (anfrage.method !== 'GET') return;

  const url = new URL(anfrage.url);
  if (url.origin !== self.location.origin) return;
  if (!url.pathname.startsWith(WURZEL)) return;
  if (url.pathname === inApp('version.json')) return;   // nie cachen

  if (istTon(url)) return e.respondWith(tonAusliefern(anfrage, url));
  if (url.pathname.startsWith(inApp('api/'))) return e.respondWith(netzZuerst(anfrage));
  e.respondWith(ausDerSchale(anfrage));
});

/**
 * Alles aus dem Mantel dieser Fassung; was fehlt, wird geholt und abgelegt.
 *
 * Cache zuerst ist hier richtig und schnell: Solange dieser Worker aktiv ist,
 * gehört alles im Mantel **zu einer Fassung**. Ein neuer Worker wartet, statt
 * dazwischenzufunken.
 */
async function ausDerSchale(anfrage) {
  const cache = await schale();
  if (!cache) return fetch(anfrage);

  const drin = await cache.match(anfrage);
  if (drin) return drin;
  try {
    const antwort = await fetch(anfrage);
    if (antwort && antwort.ok) cache.put(anfrage, antwort.clone());
    return antwort;
  } catch (fehler) {
    if (anfrage.mode === 'navigate') {
      const huelle = await cache.match(inApp('index.html'));
      if (huelle) return huelle;
    }
    throw fehler;
  }
}

// ---- API -----------------------------------------------------------------

async function netzZuerst(anfrage) {
  const gesichert = await (await caches.open(LEKTIONEN)).match(anfrage.url);
  if (gesichert) return gesichert;

  const cache = await caches.open(API);
  try {
    const antwort = await fetch(anfrage);
    if (antwort && antwort.ok) cache.put(anfrage, antwort.clone());
    return antwort;
  } catch {
    const drin = await cache.match(anfrage);
    if (drin) return drin;
    return new Response(JSON.stringify({
      fehler: 'offline',
      grund: 'Kein Netz zum Server, und diese Antwort liegt nicht im Gerät. Was '
           + 'offline gesichert wurde, ist weiter erreichbar.',
    }), { status: 503, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
  }
}

// ---- Tonspur -------------------------------------------------------------

const istTon = (url) =>
  url.pathname.startsWith(inApp('api/lektion/')) && url.pathname.endsWith('/audio.mp3');

/**
 * Der Ton aus dem Cache — mit `Range` von Hand.
 *
 * Das ist der Punkt, an dem Offline-Audio in PWAs üblicherweise bricht: Ein
 * <audio>-Element fragt in Stücken, im Cache liegt aber die ganze Datei als
 * eine 200-Antwort. Also wird hier zugeschnitten und ein echtes 206 gebaut.
 */
async function tonAusliefern(anfrage, url) {
  const cache = await caches.open(LEKTIONEN);
  const drin = await cache.match(url.pathname);
  if (!drin) {
    try {
      return await fetch(anfrage);
    } catch {
      return new Response(
        'Diese Lektion wurde nicht offline gesichert, und der Server ist nicht erreichbar.',
        { status: 504, headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
    }
  }

  const bereich = anfrage.headers.get('range');
  if (!bereich) return drin;
  const daten = await drin.arrayBuffer();
  const treffer = /bytes=(\d*)-(\d*)/.exec(bereich);
  if (!treffer) return drin;

  const gesamt = daten.byteLength;
  let von = treffer[1] ? Number(treffer[1]) : 0;
  let bis = treffer[2] ? Number(treffer[2]) : gesamt - 1;
  if (!treffer[1] && treffer[2]) {
    von = Math.max(0, gesamt - Number(treffer[2]));
    bis = gesamt - 1;
  }
  von = Math.max(0, Math.min(von, gesamt - 1));
  bis = Math.max(von, Math.min(bis, gesamt - 1));

  return new Response(daten.slice(von, bis + 1), {
    status: 206,
    statusText: 'Partial Content',
    headers: {
      'Content-Type': drin.headers.get('Content-Type') || 'audio/mpeg',
      'Content-Range': `bytes ${von}-${bis}/${gesamt}`,
      'Content-Length': String(bis - von + 1),
      'Accept-Ranges': 'bytes',
    },
  });
}
