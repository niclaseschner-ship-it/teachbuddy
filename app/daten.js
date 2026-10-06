// Die Daten der App — seit 11.09.2026 vom Dienst statt aus dieser Datei.
//
// **Was sich geaendert hat und was nicht.** Bis heute standen hier Mock-Daten
// als Konstanten; die Ansichten haben sie so benutzt, wie sie hier lagen.
// Geaendert ist nur die **Quelle**: Dieselben Namen, dieselben Formen, aber
// geholt von `/api/lernpfad/P-01`. Kein Aufrufer musste angefasst werden.
//
// `BASIS` statt absoluter Pfade: Die App laeuft direkt unter `/` oder hinter
// einem Reverse-Proxy unter einem Unterpfad wie `/teachbuddy/`. Ein `/api/...` im Quelltext
// zeigte dort auf einen fremden Dienst.

import { zustandVon, fortschritt as fortschrittVon } from './zustand.js';

/** Wo die App liegt — aus dem eigenen Modulpfad, nicht fest verdrahtet. */
const BASIS = new URL('./', import.meta.url);
const weg = (p) => new URL(String(p).replace(/^\/+/, ''), BASIS).pathname;

// **Alle Lernpfade, nicht nur P-01.** Bis zum 13.09.2026 stand hier ein fest
// verdrahtetes `api/lernpfad/P-01`. Mit dem zweiten Lernpfad waren dessen vier
// Kapitel und 29 Lektionen damit unerreichbar — gebaut, aber unsichtbar.
/** Sagt, was los ist, statt eine weisse Seite zu hinterlassen.
 *
 * Am 13.09.2026 lud die App auf dem Telefon nicht mehr und zeigte nichts —
 * kein Fehler, keine Zeile, weiss. Ein `throw` im Modulkopf bricht die Seite
 * ab, bevor irgendetwas gezeichnet ist. Wer nichts sieht, kann nichts melden.
 */
function scheitern(satz, rat) {
  const ziel = document.getElementById('app') || document.body;
  ziel.innerHTML = `<div style="padding:24px;max-width:34rem;font:16px/1.6 system-ui">
    <h1 style="font-size:19px;margin:0 0 10px">TeachBuddy lädt nicht</h1>
    <p style="margin:0 0 10px">${satz}</p>
    <p style="margin:0 0 16px;color:#6A7078;font-size:14px">${rat}</p>
    <button onclick="location.reload()" style="padding:9px 16px;font:inherit;
      font-size:14px;border:1px solid #DCD5C7;border-radius:8px;background:#FCFBF8">
      Nochmal versuchen</button></div>`;
  throw new Error(satz);
}

let antwort;
try {
  antwort = await fetch(weg('api/lernpfade'));
} catch (f) {
  scheitern('Der Server ist nicht erreichbar.',
            'Läuft der TeachBuddy-Dienst, und ist der Server von diesem Gerät aus erreichbar?');
}
if (!antwort.ok) {
  scheitern(`Der Dienst antwortet mit ${antwort.status}.`,
            'Läuft teachbuddy-dienst? <code>sudo systemctl status teachbuddy-dienst</code>');
}
const alle = (await antwort.json()).lernpfade || [];
if (!alle.length) {
  scheitern('Der Dienst kennt keinen Lernpfad.',
            'Der Index ist vermutlich leer — <code>python3 -m bibliothek.index</code>');
}

// Die Kapitel aller Pfade in einer Liste, jedes mit seinem Pfad als Herkunft.
const roh = {
  kapitel: alle.flatMap((p) => (p.kapitel || []).map((k) => ({
    ...k, pfad_id: p.lernpfad.id, pfad_titel: p.lernpfad.titel,
  }))),
};
const pfad = alle[0].lernpfad;

/** Die Lernpfade selbst — die Übersicht gruppiert nach ihnen. */
export const lernpfade = alle.map((p) => ({
  ...p.lernpfad,
  kapitel: (p.kapitel || []).map((k) => k.id),
}));

export const lernpfad = {
  id: pfad.id,
  titel: alle.length === 1 ? pfad.titel : 'TeachBuddy',
  kurzfassung: alle.length === 1 ? pfad.kurzfassung
    : alle.map((p) => p.lernpfad.titel).join(' · '),
  kapitel_gesamt: roh.kapitel.length,
};

// `echt` heisst hier: das Kapitel hat mindestens eine **gebaute** Lektion.
// Seit dem 12.09.2026 liefert der Dienst auch die geplanten mit (`geplant:
// true`), damit das Kapitel seine ganze Groesse zeigt und nicht so aussieht,
// als waere es fertig. Die Ansicht daempft sie.
const vomDienst = (roh.kapitel || []).map((k, i) => ({
  id: k.id,
  nummer: k.nummer ?? i + 1,
  titel: k.titel,
  kurzfassung: k.kurzfassung,
  hat_mindmap: k.hat_mindmap ?? false,
  hat_diskussion: k.hat_diskussion ?? false,
  pfad_id: k.pfad_id,
  pfad_titel: k.pfad_titel,
  echt: (k.lektionen || []).some((l) => !l.geplant),
  lektionen: (k.lektionen || []).map((l, j) => ({
    ...l,
    nummer: l.nummer ?? j + 1,
  })),
}));

export const kapitel = vomDienst;

export const fortschritt = fortschrittVon;

export const gesamt = kapitel.reduce((acc, k) => {
  const f = fortschritt(k);
  return {
    lektionen: acc.lektionen + f.gesamt,
    geplant: acc.geplant + f.geplant,
    gehoert: acc.gehoert + f.gehoert,
    geprueft: acc.geprueft + f.geprueft,
  };
}, { lektionen: 0, geplant: 0, gehoert: 0, geprueft: 0 });

// Weiterhören (OBF-5): die zuletzt angefangene Lektion.
export const weiterhoeren = (() => {
  for (const k of kapitel) {
    const l = k.lektionen.find((x) => !x.geplant && zustandVon(x) === 'angefangen');
    if (l) return { kapitel: k, lektion: l };
  }
  return null;
})();

export const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.round(s) % 60).padStart(2, '0')}`;
