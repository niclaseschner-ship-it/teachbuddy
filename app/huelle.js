// Gemeinsame Hülle der drei Varianten: Kopf, Weiterhören, Kapitel-Werkzeuge, Fuß.
// Nur die Kapitel- und Lektionszeile unterscheidet sich je Variante.

import { lernpfad, gesamt, weiterhoeren, mmss } from './daten.js';

export const ikon = {
  play: '<svg viewBox="0 0 12 14"><path d="M0 0l12 7-12 7z"/></svg>',
  pfeil: '<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M5 2l5 5-5 5"/></svg>',
  mindmap: '<svg viewBox="0 0 16 16"><circle cx="3" cy="8" r="1.8"/><circle cx="13" cy="4" r="1.8"/><circle cx="13" cy="12" r="1.8"/><path d="M4.8 8h2.7M7.5 8l3.8-3.6M7.5 8l3.8 3.6"/></svg>',
  diskussion: '<svg viewBox="0 0 16 16"><path d="M14 9.5a1.5 1.5 0 0 1-1.5 1.5H6l-3.5 2.5V4A1.5 1.5 0 0 1 4 2.5h8.5A1.5 1.5 0 0 1 14 4z"/></svg>',
  fragen: '<svg viewBox="0 0 16 16"><path d="M5.8 5.8a2.2 2.2 0 1 1 3 2.1c-.5.2-.8.7-.8 1.2v.4"/><circle cx="8" cy="12.4" r=".9" fill="currentColor" stroke="none"/></svg>',
  // Rückmeldung zu einer Einheit (OBF-19): eine Sprechblase mit Stift.
  sagen: '<svg viewBox="0 0 16 16"><path d="M14 8.8a1.6 1.6 0 0 1-1.6 1.6H6.4L3.2 12.6V4.4A1.6 1.6 0 0 1 4.8 2.8h3.6"/><path d="M11.2 2.2l2.1 2.1-3.3 3.3H8.1V5.5z"/></svg>',
};

export function kopf() {
  const { lektionen, gehoert, geprueft } = gesamt;
  return `
  <header>
    <div class="marke">TeachBuddy</div>
    <h1 class="pfad">${lernpfad.titel}</h1>
    <p class="pfad-kurz">${lernpfad.kurzfassung}</p>
    <div class="bilanz">
      <span><b>${gehoert}</b> von <b>${lektionen}</b> Lektionen gehört</span>
      <span>·</span>
      <span><b>${geprueft}</b> geprüft</span>
      <span>·</span>
      <span><b>${lernpfad.kapitel_gesamt}</b> Kapitel</span>
    </div>
    <div class="bilanz-bar">
      <i class="b-geprueft" style="width:${(geprueft / lektionen) * 100}%"></i>
      <i class="b-gehoert" style="width:${((gehoert - geprueft) / lektionen) * 100}%"></i>
    </div>
  </header>`;
}

/**
 * Die Adresse einer Lektion — mit Kapitel, nicht nur mit Lektion.
 *
 * `d-lektion.html` liest zwei Angaben: `l` wählt die Lektion, `k` den
 * Lernpfad, in dem sie steht. **Fehlt `l`, nimmt die Seite die erste
 * Lektion, die sie findet.** Genau das war der Fehler am 13.09.2026: Der
 * Weiterhören-Knopf zeigte einen Titel an und verlinkte `./d-lektion.html`
 * ohne jede Kennung. Er sprang also immer in dieselbe fremde Folge — die
 * erste des ersten Lernpfads. Dasselbe galt für „vorige" und „nächste" im
 * Abspieler.
 *
 * **Fehlt `k`**, nimmt die Seite den ersten Pfad mit Kapiteln. Bei einem Pfad
 * ging das gut. Seit es P-01 und P-02 gibt, findet sie das Kapitel der
 * Lektion dann unter Umständen nicht, und die Nachbarknöpfe verschwinden.
 *
 * Titel sind keine Identität. Diese Funktion ist die Stelle, an der die Adresse nicht mehr von
 * Hand zusammengesetzt wird.
 */
export function lektionsWeg(lektion, kapitel, { ziel = './d-lektion.html' } = {}) {
  const felder = new URLSearchParams();
  const kapitelId = kapitel?.id ?? lektion?.kapitel_id;
  if (kapitelId) felder.set('k', kapitelId);
  if (lektion?.id) felder.set('l', lektion.id);
  const frage = felder.toString();
  return frage ? `${ziel}?${frage}` : ziel;
}

// Weiterhören führt ins Lektions-Untermenü, es spielt nicht selbst ab.
// Die Übersicht navigiert, sie bedient nicht.
export function weiter({ ziel = './d-lektion.html' } = {}) {
  if (!weiterhoeren) return '';
  const { kapitel: k, lektion: l } = weiterhoeren;
  const anteil = (l.position_sek / l.dauer_sek) * 100;
  return `
  <a class="weiter" href="${lektionsWeg(l, k, { ziel })}">
    <span class="weiter-text">
      <span class="weiter-label">Weiterhören</span>
      <div class="weiter-titel">${l.titel}</div>
      <div class="weiter-meta">Kapitel ${k.nummer} · ${mmss(l.position_sek)} von ${mmss(l.dauer_sek)}</div>
      <div class="weiter-bar"><i style="width:${anteil}%"></i></div>
    </span>
    <span class="weiter-pfeil">${ikon.pfeil}</span>
  </a>`;
}

// Der eine Einstieg ins Kapitel-Untermenü. Er ersetzt die frühere Reihe aus
// Mindmap-, Diskussions- und Fragen-Pillen: diese drei liegen jetzt alle im
// Kapitel-Untermenü, und drei Knöpfe für ein Ziel sind drei zu viel.
export function kapitelEinstieg(k, { ziel = './e-kapitel.html' } = {}) {
  const teile = [];
  if (k.hat_mindmap) teile.push('Mindmap');
  if (k.hat_diskussion) teile.push('Gespräch');
  teile.push('alle Lektionen');
  return `
  <a class="k-einstieg" href="${ziel}">
    <span class="k-einstieg-text">
      <b>Kapitel öffnen</b>
      <i>${teile.join(' · ')}</i>
    </span>
    <span class="k-einstieg-pfeil">${ikon.pfeil}</span>
  </a>`;
}

export function werkzeuge(k) {
  return `
  <div class="k-werkzeuge">
    ${k.hat_mindmap ? `<button class="werkzeug">${ikon.mindmap} Mindmap</button>` : ''}
    ${k.hat_diskussion ? `<button class="werkzeug">${ikon.diskussion} Diskussion</button>` : ''}
    <button class="werkzeug">${ikon.fragen} Fragen des Kapitels</button>
  </div>`;
}

const HINWEIS_UEBERSICHT = `
  Kapitel und Lektionen kommen vom Dienst; Kapitel ohne Lektion sagen das.
  Die <i>kursiv gedämpften</i> Kapitel sind Struktur ohne Inhalt: 15 Kapitel und 65 Lektionen,
  damit die volle Last sichtbar ist. Es wird kein Lerninhalt erfunden.`;

/** Zusatzinfo, die nur erscheint, wenn man sie aufklappt.
 *
 * Rückmeldung vom 11.09.2026: „alles was Zusatzinfo ist bitte zum aufklappen und damit
 * nur wenn ich es brauche". Der Inhalt ist nicht weg, er ist nur nicht im Weg.
 */
export function beiBedarf(titel, inhalt) {
  if (!inhalt) return '';
  return `<details class="bei-bedarf"><summary>${titel}</summary>
    <div class="bei-bedarf-inhalt">${inhalt}</div></details>`;
}

/** Die stille Fußzeile: welche Fassung läuft, und der Weg zum Zurücksetzen.
 *
 * Sie steht unten, klein und grau. Rückmeldung vom 13.09.2026: „klein, nicht
 * prominent, irgendwo". Der Notausgang muss auffindbar sein, ohne sich
 * anzubieten — wer ihn braucht, sucht ihn.
 *
 * Die Fassung daneben ist kein Schmuck: Sie beantwortet die Frage, die bei
 * jedem Cache-Verdacht zuerst kommt — hat mein Gerät überhaupt den aktuellen
 * Stand? Vergleichen kann man sie mit dem, was der Server unter `/version.json`
 * ausliefert.
 */
export function fusszeile() {
  return `<footer class="huelle-fuss">
    <span id="fassung">…</span>
    <a href="./neustart.html">zurücksetzen</a>
  </footer>`;
}

/** Trägt die laufende Fassung in die Fußzeile ein. */
export async function fassungZeigen() {
  const ziel = document.getElementById('fassung');
  if (!ziel) return;
  try {
    const basis = new URL('./', import.meta.url);
    const a = await fetch(new URL('version.json', basis).pathname, { cache: 'no-store' });
    const f = (await a.json()).fassung || '?';
    ziel.textContent = `Fassung ${f.slice(0, 8)}`;
  } catch {
    // Ohne Server keine Fassung. Das ist keine Störung, sondern der Offline-Fall.
    ziel.textContent = 'offline';
  }
}

export function aufklappen(wurzel) {
  wurzel.querySelectorAll('.k-kopf').forEach((kopf) => {
    kopf.addEventListener('click', () => {
      const k = kopf.closest('.kapitel');
      const offen = k.classList.toggle('offen');
      k.toggleAttribute('open', offen);
      kopf.setAttribute('aria-expanded', String(offen));
    });
  });
}
