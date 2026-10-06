// Mindmap — der Knotenbaum eines Kapitels, gezeichnet als SVG.
//
// E-19b sagt, was das hier ist und was es nicht ist: **eine Ansicht auf den
// Begriffsgraphen**, keine gezeichnete Grafik. Daraus folgt alles Weitere —
// Knoten sind anklickbar und zeigen Kurzfassung samt Belegen (MMP-6), der
// Lernstand faerbt sie (MMP-7), Querbezuege sind sichtbar (MMP-5), und vom
// Knoten fuehrt ein Weg in die Lektion.
//
// Warum das SVG **in der Seite** steht und nicht wie die Lektionsbilder in
// einem Rahmen (bildschau.js): Ein Bild ist dort ein eigenstaendiges Dokument
// hinter `pointer-events: none` und `aria-hidden`. Genau das kann eine
// Mindmap nicht gebrauchen — kein Klick kaeme an, und das Suchen des Browsers
// findet keinen Text in einem fremden Dokument. Die Bedienung der Bildschau
// bleibt trotzdem dieselbe: Rad zoomt, ein Zeiger schiebt, zwei zoomen,
// Doppeltippen wechselt zwischen eingepasst und 1:1, Escape schliesst.
//
// Gezeichnet wird nur, was der Dienst liefert. Wo ein Feld fehlt, steht die
// Luecke in der Fussnote statt einer plausiblen Antwort (CONTRIBUTING.md, Regel 2).

/** Wo die App liegt — direkt unter / oder hinter einem Proxy unter einem Unterpfad. */
const BASIS = new URL('./', import.meta.url);
const weg = (p) => new URL(String(p).replace(/^\/+/, ''), BASIS).pathname;

const roh = (t) => String(t ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// Die Bibliothek schreibt Hervorhebungen als Markdown (`**beiden**`). Sie
// stehen zu lassen waere kein Beleg von Treue, sondern nur unaufgeraeumt;
// mehr als Fettung wird aber nicht uebersetzt.
const fett = (t) => roh(t).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');

// --- Masze -----------------------------------------------------------------
// Die Knoten tragen seit dem 11.09.2026 **Stichworte** (MMP-3), nicht mehr
// ganze Saetze. Die Behauptung steht weiter am Knoten, aber in `satz` und
// damit auf der Tafel, nicht im Kasten. Deshalb ist der Kasten schmal wie im
// Design-Entwurf; vorher war er 216 breit, weil ein Satz hineinmusste.

const B = 158;            // Knotenbreite
const SPALTE = 58;        // Luft zwischen den Spalten
const ZEILE = 14;         // Luft zwischen den Knoten
const RAND = 14;          // Rand um die ganze Karte
const PAD_X = 14, PAD_O = 11, PAD_U = 10;
const AKZENT = 4;         // Breite des Zustandsbalkens links
const TEXT_B = B - PAD_X * 2 - AKZENT;
const LINIE = 15;         // Zeilenhoehe der Beschriftung
const META = 15;          // Zeile mit Belegzahl und Lektionssprung
const SCHALTER = 9;       // Radius des Auf-/Zuklappers
const KARTE_HOCH = 420;   // Hoehe der Buehne in der Karte (wie bildKarte heute)
const VIELE = 25;         // ab so vielen Knoten startet die Karte zugeklappt

const SCHRIFT = 'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif';

const ZUSTAND_TEXT = {
  ungehoert: 'ungehört',
  angefangen: 'angefangen',
  gehoert: 'gehört',
  fragen_beantwortet: 'Fragen beantwortet',
};

// --- Messen ----------------------------------------------------------------
// Ein SVG bricht Text nicht selbst um. Gemessen wird auf einer Leinwand mit
// derselben Schrift; die 2 % Zuschlag fangen den Unterschied zwischen
// Leinwand- und SVG-Rasterung auf.

const latte = document.createElement('canvas').getContext('2d');
function breiteVon(text, groesse = 12.5, gewicht = 400) {
  latte.font = `${gewicht} ${groesse}px ${SCHRIFT}`;
  return latte.measureText(text).width * 1.02;
}

function umbruch(text, maxBreite, groesse = 12.5, gewicht = 400) {
  const worte = String(text ?? '').split(/\s+/).filter(Boolean);
  const zeilen = [];
  let zeile = '';
  for (const wort of worte) {
    const probe = zeile ? `${zeile} ${wort}` : wort;
    if (zeile && breiteVon(probe, groesse, gewicht) > maxBreite) {
      zeilen.push(zeile);
      zeile = wort;
    } else {
      zeile = probe;
    }
  }
  if (zeile) zeilen.push(zeile);
  return zeilen.length ? zeilen : ['—'];
}

// --- Baum ------------------------------------------------------------------

/** Flache Liste aller Knoten, in der Reihenfolge des Baums. */
function alleKnoten(knoten, tiefe = 0, sammler = []) {
  sammler.push({ knoten, tiefe });
  for (const kind of knoten.kinder || []) alleKnoten(kind, tiefe + 1, sammler);
  return sammler;
}

function vermessen(knoten) {
  const wurzel = knoten.art === 'wurzel';
  const achse = knoten.art === 'achse';
  const gross = wurzel ? 13.5 : achse ? 13 : 12.5;
  knoten._zeilen = umbruch(knoten.label, TEXT_B, gross, wurzel || achse ? 650 : 400);
  // Wurzel und Achse tragen keine Belege und fuehren in keine Lektion; eine
  // Metazeile waere dort leer.
  knoten._meta = !wurzel && !achse;
  knoten._h = PAD_O + knoten._zeilen.length * LINIE + (knoten._meta ? META : 0) + PAD_U;
  for (const kind of knoten.kinder || []) vermessen(kind);
}

/**
 * Links-nach-rechts, wie der Platzhalter es zeigt: Die Tiefe bestimmt die
 * Spalte, die Blaetter werden von oben nach unten gestapelt, und ein Elter
 * steht auf der Mitte seiner Kinder. Wo ein Elter dadurch in seinen Vorgaenger
 * liefe, rutscht sein ganzer Teilbaum nach unten — sonst ueberlagern sich
 * Zweige, sobald einer tief und einer flach ist.
 */
function legeAus(wurzel, offen) {
  const spalten = [];     // unterste belegte Kante je Spalte
  let laufend = RAND;     // gemeinsamer Stapel der Blaetter

  const kinderVon = (k) => (offen.has(k.id) ? (k.kinder || []) : []);

  const verschiebe = (k, tiefe, dy) => {
    k._y += dy;
    spalten[tiefe] = Math.max(spalten[tiefe] ?? 0, k._y + k._h + ZEILE);
    for (const kind of kinderVon(k)) verschiebe(kind, tiefe + 1, dy);
  };

  const setze = (k, tiefe) => {
    k._x = RAND + tiefe * (B + SPALTE);
    const kinder = kinderVon(k);
    if (!kinder.length) {
      k._y = Math.max(laufend, spalten[tiefe] ?? 0);
    } else {
      for (const kind of kinder) setze(kind, tiefe + 1);
      const oben = kinder[0]._y;
      const unten = kinder[kinder.length - 1]._y + kinder[kinder.length - 1]._h;
      k._y = (oben + unten) / 2 - k._h / 2;
      const grenze = spalten[tiefe] ?? RAND;
      if (k._y < grenze) verschiebe(k, tiefe, grenze - k._y);
      if (k._y < RAND) verschiebe(k, tiefe, RAND - k._y);
    }
    spalten[tiefe] = Math.max(spalten[tiefe] ?? 0, k._y + k._h + ZEILE);
    laufend = Math.max(laufend, k._y + k._h + ZEILE);
  };

  setze(wurzel, 0);

  let breite = 0, hoehe = 0;
  const sichtbar = [];
  const sammle = (k) => {
    sichtbar.push(k);
    breite = Math.max(breite, k._x + B + SCHALTER * 2);
    hoehe = Math.max(hoehe, k._y + k._h);
    for (const kind of kinderVon(k)) sammle(kind);
  };
  sammle(wurzel);
  return { sichtbar, breite: breite + RAND, hoehe: hoehe + RAND };
}

// --- Zeichnen --------------------------------------------------------------

function ast(elter, kind) {
  const x1 = elter._x + B, y1 = elter._y + elter._h / 2;
  const x2 = kind._x, y2 = kind._y + kind._h / 2;
  const m = x1 + (x2 - x1) / 2;
  return `<path class="mm-ast" d="M${x1} ${y1} C${m} ${y1} ${m} ${y2} ${x2} ${y2}"/>`;
}

function belegWort(n) {
  const zahl = (n.belege || []).length;
  if (!zahl) return n.art === 'wurzel' ? '' : 'ohne Beleg';
  return zahl === 1 ? '1 Beleg' : `${zahl} Belege`;
}

function knotenSvg(k, { offen, gewaehlt }) {
  const wurzel = k.art === 'wurzel';
  const zustand = k.zustand || null;
  const kinder = k.kinder || [];
  const auf = offen.has(k.id);
  const klassen = [
    'mm-knoten',
    `mm-art-${k.art || 'begriff'}`,
    `mm-z-${zustand || 'ohne'}`,
    k.strittig ? 'mm-ist-strittig' : '',
    gewaehlt === k.id ? 'mm-gewaehlt' : '',
  ].filter(Boolean).join(' ');

  const textX = k._x + AKZENT + PAD_X;
  const ersteBasis = k._y + PAD_O + 11.5;
  const zeilen = k._zeilen
    .map((z, i) => `<tspan x="${textX}" y="${ersteBasis + i * LINIE}">${roh(z)}</tspan>`)
    .join('');

  let meta = '';
  if (k._meta) {
    const basis = k._y + k._h - PAD_U - 3;
    const teile = [];
    let links = textX;
    if (k.strittig) {
      teile.push(
        `<rect class="mm-pille" x="${links}" y="${basis - 11}" width="46" height="15" rx="7.5"/>`
        + `<text class="mm-pille-text" x="${links + 8}" y="${basis}">strittig</text>`);
      links += 52;
    }
    const wort = belegWort(k);
    if (wort) teile.push(`<text class="mm-belege" x="${links}" y="${basis}">${wort}</text>`);
    const sprung = k.lektion ? `→ ${k.lektion}` : 'ohne Lektion';
    teile.push(`<text class="mm-lektion ${k.lektion ? '' : 'mm-luecke'}" x="${k._x + B - PAD_X}" y="${basis}" text-anchor="end">${roh(sprung)}</text>`);
    meta = teile.join('');
  }

  const schalter = kinder.length
    ? `<g class="mm-schalter" data-klappen="${roh(k.id)}">
         <circle cx="${k._x + B}" cy="${k._y + k._h / 2}" r="${SCHALTER}"/>
         <path d="M${k._x + B - 4.5} ${k._y + k._h / 2}h9${auf ? '' : `M${k._x + B} ${k._y + k._h / 2 - 4.5}v9`}"/>
       </g>${auf ? '' : `<text class="mm-zahl" x="${k._x + B + SCHALTER + 4}" y="${k._y + k._h / 2 + 4}">${kinder.length}</text>`}`
    : '';

  const hut = zustand ? `<rect class="mm-akzent" x="${k._x}" y="${k._y}" width="${AKZENT}" height="${k._h}" rx="2"/>` : '';

  return `
    <g class="${klassen}" data-knoten="${roh(k.id)}" tabindex="0" role="button"
       ${kinder.length ? `aria-expanded="${auf}"` : ''}
       aria-label="${roh(k.label)}${zustand ? `, ${ZUSTAND_TEXT[zustand] || zustand}` : ''}${k.strittig ? ', strittig' : ''}">
      <title>${roh(k.kurzfassung || k.label)}</title>
      <rect class="mm-rahmen" x="${k._x}" y="${k._y}" width="${B}" height="${k._h}" rx="9"/>
      ${hut}
      <text class="mm-label">${zeilen}</text>
      ${meta}
    </g>${schalter}`;
}

/** Querbezuege (MMP-5) — nur fuer den gewaehlten Knoten, sonst ist die Karte zu. */
function querSvg(quelle, ziele) {
  return ziele.map((z) => {
    const x1 = quelle._x + B / 2, y1 = quelle._y + quelle._h / 2;
    const x2 = z._x + B / 2, y2 = z._y + z._h / 2;
    const bogen = Math.max(40, Math.abs(y2 - y1) / 2);
    return `<path class="mm-quer-linie" d="M${x1} ${y1} C${x1 + bogen} ${y1} ${x2 + bogen} ${y2} ${x2} ${y2}"/>`;
  }).join('');
}

// --- Tafel: was ein Knoten zeigt, wenn man ihn antippt (MMP-6) --------------

function belegHtml(id, belege) {
  const b = belege?.[id];
  if (!b) {
    return `<li class="mm-beleg mm-fehlt"><b>${roh(id)}</b> — liegt nicht ausgeschrieben vor.
      Der Vertrag schreibt Belege ausgeschrieben mit (R-5); dieser fehlt im Block <code>belege</code>.</li>`;
  }
  const marken = [
    b.quelle_id ? `<span class="mm-marke">${roh(b.quelle_id)}</span>` : '',
    b.zuversicht ? `<span class="mm-marke">Zuversicht ${roh(b.zuversicht)}</span>` : '',
    b.freigegeben === false ? '<span class="mm-marke mm-marke-offen">nicht freigegeben</span>' : '',
  ].join('');
  return `
    <li class="mm-beleg">
      <div class="mm-beleg-kopf"><b>${roh(id)}</b>${marken}</div>
      ${b.aussage ? `<p class="mm-aussage">${fett(b.aussage)}</p>` : ''}
      ${b.zitat ? `<blockquote>${fett(b.zitat)}</blockquote>` : ''}
      ${b.stelle ? `<div class="mm-stelle">${roh(b.stelle)}</div>` : ''}
    </li>`;
}

function tafelHtml(k, daten, quer) {
  if (!k) {
    return `<p class="mm-leer mm-wink">Einen Knoten antippen: Kurzfassung, Belege und der Weg
      in die Lektion stehen dann hier. Der Baum klappt an den Kreisen auf und zu.</p>`;
  }
  const marken = [
    k.zustand ? `<span class="mm-marke mm-z-${k.zustand}">${ZUSTAND_TEXT[k.zustand] || k.zustand}</span>` : '',
    k.grad ? `<span class="mm-marke">${roh(k.grad)}</span>` : '',
    k.strittig ? '<span class="mm-marke mm-marke-strittig">strittig</span>' : '',
    k.wissenseinheit ? `<span class="mm-marke">${roh(k.wissenseinheit)}</span>` : '',
  ].join('');

  const belege = k.belege || [];
  const querHtml = quer.length
    ? `<div class="mm-quer">Querbezug (MMP-5):
        ${quer.map((z) => `<button type="button" class="mm-sprungmarke" data-zeige="${roh(z.knoten ? z.knoten.id : '')}"
            ${z.knoten ? '' : 'disabled'}>${roh(z.we)}${z.knoten ? '' : ' — nicht in diesem Kapitel'}</button>`).join('')}
       </div>`
    : '';

  return `
    <div class="mm-tafel-kopf">${marken}</div>
    <h3 class="mm-tafel-titel">${roh(k.label)}</h3>
    ${k.satz && k.satz !== k.label ? `<p class="mm-satz">${fett(k.satz)}</p>` : ''}
    ${k.kurzfassung
      ? `<p class="mm-kurz">${fett(k.kurzfassung)}</p>`
      : ''}
    ${k.lektion
      ? `<a class="mm-sprung" href="${weg('d-lektion.html')}?l=${encodeURIComponent(k.lektion)}">Zur Lektion ${roh(k.lektion)} →</a>`
      : (k.art === 'wurzel' ? '' : '<p class="mm-fehlt">Zu diesem Begriff gibt es noch keine Lektion.</p>')}
    ${querHtml}
    ${belege.length
      ? `<details class="mm-belege" open>
           <summary>${belegWort(k)}</summary>
           <ul>${belege.map((id) => belegHtml(id, daten.belege)).join('')}</ul>
         </details>`
      : (k.art === 'wurzel' ? '' : '<p class="mm-fehlt">Noch keine Belege an diesem Begriff.</p>')}`;
}


// --- Gestalt ---------------------------------------------------------------
// Eigene Klassen, alle mit `mm-` davor, und eine eigene Palette: Die Flaeche
// der Mindmap ist Papier wie die der Lektionsbilder (#E7E3DA), unabhaengig
// davon, ob die App hell oder dunkel laeuft. Die Bedeutungsfarben sind die
// hellen Varianten aus stil.css — hoeren, geprueft, strittig. Dort wird
// nichts geaendert (AUFTRAG: nichts umgestalten).

const STIL = `
.mm { --mm-papier:#E7E3DA; --mm-karte:#FCFBF8; --mm-kante:#DCD5C7; --mm-ast:#C6BFB1;
      --mm-text:#33383E; --mm-text-2:#6A7078; --mm-text-3:#9A9384; --mm-dunkel:#22262B;
      --mm-ungehoert:#CFC8BB; --mm-angefangen:#DDA15E; --mm-gehoert:#B57722;
      --mm-geprueft:#2F8F6D; --mm-streit:#B25B31; --mm-streit-matt:#F2DDD2;
      --mm-fokus:#2F5FC4;
      display:flex; flex-direction:column; min-width:0; }

.mm-leiste { display:flex; align-items:center; gap:8px; flex-wrap:wrap;
  padding:4px 16px 10px; font-size:12.5px; color:var(--text-3); }
.mm-leiste-titel { flex:1; min-width:120px; }
.mm-k { min-width:32px; height:28px; padding:0 9px; background:var(--flaeche-hoch);
  border:1px solid var(--linie); color:var(--text-2); border-radius:var(--r-klein);
  font:inherit; font-size:12.5px; cursor:pointer; }
.mm-k:hover { color:var(--text); border-color:var(--text-3); }
.mm-stufe { font-variant-numeric:tabular-nums; min-width:58px; }

.mm-buehne { position:relative; background:var(--mm-papier); overflow:hidden;
  touch-action:none; user-select:none; cursor:grab; height:${KARTE_HOCH}px; }
.mm-buehne.schiebt { cursor:grabbing; }
.mm-buehne svg { display:block; width:100%; height:100%; font-family:${SCHRIFT}; }

.mm-ast { fill:none; stroke:var(--mm-ast); stroke-width:1.6; }
.mm-quer-linie { fill:none; stroke:var(--mm-fokus); stroke-width:1.4; stroke-dasharray:5 4; opacity:.75; }
.mm-knoten { cursor:pointer; }
.mm-knoten .mm-rahmen { fill:var(--mm-karte); stroke:var(--mm-kante); stroke-width:1; }
.mm-knoten:hover .mm-rahmen { stroke:var(--mm-text-3); }
.mm-knoten:focus { outline:none; }
.mm-art-wurzel .mm-rahmen { fill:var(--mm-dunkel); stroke:var(--mm-dunkel); }
.mm-art-wurzel .mm-label { fill:#FBF9F5; font-size:13.5px; font-weight:650; }
/* Die Achse ist die Frage, nach der sortiert wurde. Sie ist Gliederung, kein
   Begriff — dunkler und halbfett, wie im Design-Entwurf. */
.mm-art-achse .mm-label { fill:var(--mm-dunkel); font-size:13px; font-weight:650; }
.mm-art-achse .mm-akzent { fill:var(--mm-kante); }
.mm-label { fill:var(--mm-text); font-size:12.5px; }
.mm-belege { fill:var(--mm-text-2); font-size:10.5px; }
.mm-lektion { fill:var(--mm-text-3); font-size:10px; letter-spacing:.03em; }
.mm-lektion.mm-luecke { fill:var(--mm-streit); font-style:italic; }
.mm-zahl { fill:var(--mm-text-3); font-size:10.5px; }
.mm-pille { fill:var(--mm-streit-matt); }
.mm-pille-text { fill:var(--mm-streit); font-size:10px; font-weight:700; }
.mm-ist-strittig .mm-rahmen { stroke:var(--mm-streit); stroke-dasharray:5 3; }
/* Die Wahl gewinnt gegen die Strittig-Kante: Der gestrichelte Rand ist nur die
   halbe Marke, die Pille im Knoten bleibt ohnehin stehen. */
.mm-knoten:focus-visible .mm-rahmen, .mm-knoten.mm-gewaehlt .mm-rahmen {
  stroke:var(--mm-fokus); stroke-width:2; stroke-dasharray:none; }

.mm-akzent { fill:var(--mm-ungehoert); }
.mm-z-angefangen .mm-akzent { fill:var(--mm-angefangen); }
.mm-z-gehoert .mm-akzent { fill:var(--mm-gehoert); }
.mm-z-fragen_beantwortet .mm-akzent { fill:var(--mm-geprueft); }

.mm-schalter circle { fill:var(--mm-karte); stroke:var(--mm-kante); stroke-width:1.2; cursor:pointer; }
.mm-schalter path { stroke:var(--mm-text-2); stroke-width:1.6; stroke-linecap:round; fill:none; }
.mm-schalter:hover circle { stroke:var(--mm-fokus); }

.mm-legende { display:flex; flex-wrap:wrap; gap:4px 14px; padding:0 0 12px;
  font-size:11.5px; color:var(--text-3); }
.mm-beibedarf { border-top:1px solid var(--linie-zart); }
.mm-legende span { display:inline-flex; align-items:center; gap:5px; }
.mm-legende i { width:9px; height:9px; border-radius:2px; display:inline-block; }

/* Acht Belege mit Zitat sind laenger als die Karte hoch ist — die Tafel
   scrollt in sich, statt die Seite auseinanderzuziehen. */
.mm-tafel { padding:12px 16px 14px; border-top:1px solid var(--linie-zart);
  font-size:13.5px; color:var(--text-2); overflow:auto; max-height:460px; }
.mm-leer { margin:0; color:var(--text-3); }
.mm-wink { font-size:12.5px; line-height:1.5; }
.mm-tafel-kopf { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:7px; }
.mm-marke { display:inline-block; border:1px solid var(--linie); border-radius:999px;
  padding:1px 8px; font-size:11px; color:var(--text-3); }
.mm-marke.mm-z-angefangen, .mm-marke.mm-z-gehoert { color:var(--hoeren); border-color:var(--hoeren); }
.mm-marke.mm-z-fragen_beantwortet { color:var(--geprueft); border-color:var(--geprueft); }
.mm-marke-strittig { color:var(--strittig); border-color:var(--strittig); }
.mm-marke-offen { color:var(--strittig); border-color:var(--strittig); }
.mm-tafel-titel { margin:0 0 6px; font-family:var(--serif); font-size:16.5px;
  font-weight:600; line-height:1.3; color:var(--text); }
.mm-kurz { margin:0 0 9px; line-height:1.5; }
/* Die Behauptung der Einheit. Sie steht nicht mehr im Knoten (MMP-3), soll
   aber beim Antippen als Erstes dastehen. */
.mm-satz { margin:0 0 8px; line-height:1.45; color:var(--text);
  font-family:var(--serif); font-size:14.5px; }
.mm-sprung { display:inline-block; margin-bottom:9px; color:var(--fokus); text-decoration:none; font-size:13px; }
.mm-sprung:hover { text-decoration:underline; }
.mm-quer { margin-bottom:9px; font-size:12.5px; color:var(--text-3); }
.mm-sprungmarke { background:var(--flaeche-hoch); border:1px solid var(--linie); color:var(--text-2);
  border-radius:999px; padding:2px 9px; font:inherit; font-size:11.5px; cursor:pointer; margin:0 3px 3px 0; }
.mm-sprungmarke:hover:enabled { color:var(--fokus); border-color:var(--fokus); }
.mm-sprungmarke:disabled { cursor:default; opacity:.6; }
.mm-belege summary { cursor:pointer; font-size:12.5px; color:var(--text-3); list-style:revert; }
.mm-belege ul { list-style:none; margin:8px 0 0; padding:0; }
.mm-beleg { border-left:2px solid var(--linie); padding:0 0 0 10px; margin-bottom:11px; font-size:12.5px; }
.mm-beleg-kopf { display:flex; flex-wrap:wrap; align-items:center; gap:6px; margin-bottom:3px; color:var(--beleg); }
.mm-aussage { margin:0 0 4px; line-height:1.5; }
.mm-beleg blockquote { margin:0 0 4px; padding-left:9px; border-left:2px solid var(--linie-zart);
  color:var(--text-3); font-style:italic; line-height:1.45; }
.mm-stelle { color:var(--text-3); font-size:11.5px; }
.mm-fehlt { color:var(--strittig); }
.mm-fehler { padding:14px 16px; color:var(--strittig); font-size:13.5px; line-height:1.55; }

.mm-mitte { display:flex; flex-direction:column; min-width:0; }

/* Gross: dieselbe Bedienung wie die Bildschau, nur mit lebendigen Knoten. */
.mm.voll { position:fixed; inset:0; z-index:100; background:var(--bg); }
.mm.voll .mm-mitte { flex:1; min-height:0; }
.mm.voll .mm-buehne { flex:1; height:auto; }
.mm.voll .mm-tafel { max-height:38vh; }
.mm.voll .mm-leiste { padding-top:max(10px, env(safe-area-inset-top)); }
.mm.voll    bleibt fuer den Baum kaum mehr Platz als in der Karte. */
@media (min-width:900px) {
  .mm.voll { display:grid; grid-template-columns:1fr minmax(320px, 400px); grid-template-rows:auto 1fr; }
  .mm.voll .mm-leiste { grid-column:1 / -1; }
  .mm.voll .mm-tafel { max-height:none; border-top:0; border-left:1px solid var(--linie-zart); }
}
`;

function stilEinhaengen() {
  if (document.getElementById('mm-stil')) return;
  const s = document.createElement('style');
  s.id = 'mm-stil';
  s.textContent = STIL;
  document.head.appendChild(s);
}

// --- Karte -----------------------------------------------------------------

/**
 * Baut die Mindmap-Karte aus dem, was `/api/kapitel/<id>/mindmap` geliefert
 * hat. Fehlerantworten des Dienstes werden mitgezeichnet, nicht verschluckt.
 */
export function mindmapKarte(daten) {
  stilEinhaengen();
  const wurzel = document.createElement('div');
  wurzel.className = 'mm';

  if (!daten || daten.fehler) {
    wurzel.innerHTML = `<div class="mm-fehler"><b>Keine Mindmap:</b>
      ${roh(daten?.grund || 'Der Dienst hat nicht geantwortet.')}
      ${daten?.offen ? `<br><br>${roh(daten.offen)}` : ''}</div>`;
    return wurzel;
  }

  const baum = daten.wurzel;
  const flach = alleKnoten(baum);
  const nachId = new Map(flach.map(({ knoten }) => [knoten.id, knoten]));
  const nachEinheit = new Map(
    flach.filter(({ knoten }) => knoten.wissenseinheit).map(({ knoten }) => [knoten.wissenseinheit, knoten]));
  vermessen(baum);

  // Aufgeklappt startet, was uebersichtlich bleibt. Wird eine Bibliothek
  // groesser, waere eine offene Mindmap mit 200 Knoten keine Uebersicht mehr
  // (MMP-4) — dann stehen nur die ersten beiden Ebenen offen.
  const offen = new Set(
    flach
      .filter(({ knoten, tiefe }) => (knoten.kinder || []).length && (flach.length <= VIELE || tiefe < 1))
      .map(({ knoten }) => knoten.id));

  let gewaehlt = null;
  let s = 1, tx = 0, ty = 0, minS = .1, W = 0, H = 0;

  wurzel.innerHTML = `
    <div class="mm-leiste">
      <span class="mm-leiste-titel"><b>${flach.length}</b> Begriffe</span>
      <button type="button" class="mm-k" data-tun="klappen">alles aufklappen</button>
      <button type="button" class="mm-k" data-tun="raus" aria-label="kleiner">−</button>
      <button type="button" class="mm-k mm-stufe" data-tun="passen">100 %</button>
      <button type="button" class="mm-k" data-tun="rein" aria-label="größer">+</button>
      <button type="button" class="mm-k" data-tun="gross" aria-label="groß ansehen">⤢</button>
    </div>
    <div class="mm-mitte">
      <div class="mm-buehne"></div>
      <details class="bei-bedarf mm-beibedarf"><summary>Was die Farben bedeuten</summary>
        <div class="mm-legende">
          <span><i style="background:var(--mm-ungehoert)"></i>ungehört</span>
          <span><i style="background:var(--mm-angefangen)"></i>angefangen</span>
          <span><i style="background:var(--mm-gehoert)"></i>gehört</span>
          <span><i style="background:var(--mm-geprueft)"></i>Fragen beantwortet</span>
          <span><i style="background:var(--mm-streit)"></i>strittig (gestrichelter Rand)</span>
          <span><i style="background:var(--mm-kante)"></i>ohne Lernstand</span>
        </div>
      </details>
    </div>
    <div class="mm-tafel"></div>
`;

  const buehne = wurzel.querySelector('.mm-buehne');
  let welt = null;                     // wird bei jedem Zeichnen neu gebaut
  let fokusId = null;                  // damit die Tastatur beim Klappen nicht verliert
  const stufe = wurzel.querySelector('.mm-stufe');
  const klappKnopf = wurzel.querySelector('[data-tun="klappen"]');
  const grossKnopf = wurzel.querySelector('[data-tun="gross"]');
  const tafel = wurzel.querySelector('.mm-tafel');

  const quervonKnoten = (k) => (k?.querbezug || []).map((we) => ({ we, knoten: nachEinheit.get(we) || null }));

  const male = () => {
    if (!welt) return;
    welt.setAttribute('transform', `translate(${tx} ${ty}) scale(${s})`);
    stufe.textContent = `${Math.round(s * 100)} %`;
  };

  const zeichne = (neuPassen = false) => {
    const { sichtbar, breite, hoehe } = legeAus(baum, offen);
    W = breite; H = hoehe;
    const sichtbareIds = new Set(sichtbar.map((k) => k.id));
    const aeste = [];
    for (const k of sichtbar) {
      if (!offen.has(k.id)) continue;
      for (const kind of k.kinder || []) aeste.push(ast(k, kind));
    }
    const g = nachId.get(gewaehlt);
    const quer = g && sichtbareIds.has(g.id)
      ? querSvg(g, quervonKnoten(g).map((q) => q.knoten).filter((z) => z && sichtbareIds.has(z.id)))
      : '';
    // Als ganzes SVG in den HTML-Baum geschrieben, nicht in ein bestehendes
    // SVG hinein: `innerHTML` an einem SVG-Knoten ist junger Standard, an
    // einem <div> uralter.
    buehne.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" role="img"
           aria-label="Mindmap ${roh(daten.titel || '')}, ${sichtbar.length} sichtbare Knoten">
        <g class="mm-welt">${aeste.join('')}${quer}${sichtbar.map((k) => knotenSvg(k, { offen, gewaehlt })).join('')}</g>
      </svg>`;
    welt = buehne.querySelector('.mm-welt');
    klappKnopf.hidden = !flach.some(({ knoten }) => (knoten.kinder || []).length);
    klappKnopf.textContent = flach.some(({ knoten }) => (knoten.kinder || []).length && !offen.has(knoten.id))
      ? 'alles aufklappen' : 'alles zuklappen';
    if (fokusId) buehne.querySelector(`[data-knoten="${fokusId}"]`)?.focus();
    male();
    // Nach dem Klappen ist der Baum ein anderer — dann wird neu eingepasst.
    // Beim Waehlen eines Knotens nicht: Dort soll der Ausschnitt stehen bleiben.
    if (neuPassen) passeEin();
  };

  const zeigeTafel = () => {
    const k = nachId.get(gewaehlt);
    tafel.innerHTML = tafelHtml(k, daten, k ? quervonKnoten(k) : []);
  };

  const waehle = (id) => {
    gewaehlt = id;
    zeichne();
    zeigeTafel();
  };

  // --- Zoom und Schieben: dieselben Gesten wie in der Bildschau ------------

  // Eingepasst heiszt: der ganze Baum ist zu sehen. Eine Mindmap, von der man
  // die Haelfte erst suchen muss, ist keine Uebersicht (MMP-4).
  const passeEin = () => {
    // In der Karte ist die Buehne so hoch wie der Baum breitangepasst braucht,
    // hoechstens aber so hoch wie ein Lektionsbild. Ein Kapitel mit einem
    // einzigen Knoten bekommt keine leere Flaeche von 420 Pixeln.
    if (wurzel.classList.contains('voll')) {
      buehne.style.height = '';
    } else if (buehne.clientWidth && W) {
      const noetig = H * Math.min(1, buehne.clientWidth / W);
      buehne.style.height = `${Math.round(Math.min(KARTE_HOCH, Math.max(150, noetig)))}px`;
    }
    const r = buehne.getBoundingClientRect();
    if (!r.width || !W) return;
    // Nicht ueber 1:1 hinaus: Ein zugeklappter Baum aus einem Knoten wuerde
    // sonst auf Plakatgroesze aufgeblasen.
    s = Math.min(1, r.width / W, r.height / H);
    minS = s * 0.5;
    tx = (r.width - W * s) / 2;
    ty = (r.height - H * s) / 2;
    male();
  };

  const grenze = (w, min, max) => Math.min(max, Math.max(min, w));
  const zoomAuf = (px, py, faktor) => {
    const neu = grenze(s * faktor, minS, 8);
    tx = px - (px - tx) * (neu / s);
    ty = py - (py - ty) * (neu / s);
    s = neu;
    male();
  };
  const mitte = () => {
    const r = buehne.getBoundingClientRect();
    return [r.width / 2, r.height / 2];
  };

  buehne.addEventListener('wheel', (e) => {
    e.preventDefault();
    const r = buehne.getBoundingClientRect();
    zoomAuf(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0016));
  }, { passive: false });

  // Ein Zeiger schiebt, zwei zoomen. Gefangen wird der Zeiger erst, wenn
  // wirklich geschoben wird — sonst frisst das Schieben jeden Knotenklick.
  const zeiger = new Map();
  let letzterAbstand = 0, start = null, bewegt = 0;

  buehne.addEventListener('pointerdown', (e) => {
    fokusId = null;                    // wer tippt, will den Tastaturfokus nicht zurueck
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });
    letzterAbstand = 0;
    if (zeiger.size === 1) { start = { x: e.clientX, y: e.clientY, ziel: e.target }; bewegt = 0; }
  });

  buehne.addEventListener('pointermove', (e) => {
    if (!zeiger.has(e.pointerId)) return;
    const alt = zeiger.get(e.pointerId);
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (zeiger.size === 1) {
      bewegt += Math.hypot(e.clientX - alt.x, e.clientY - alt.y);
      if (bewegt < 6) return;
      if (!buehne.hasPointerCapture(e.pointerId)) {
        buehne.setPointerCapture(e.pointerId);
        buehne.classList.add('schiebt');
      }
      tx += e.clientX - alt.x;
      ty += e.clientY - alt.y;
      male();
      return;
    }
    if (zeiger.size === 2) {
      const [a, b] = [...zeiger.values()];
      const abstand = Math.hypot(a.x - b.x, a.y - b.y);
      if (letzterAbstand) {
        const r = buehne.getBoundingClientRect();
        zoomAuf((a.x + b.x) / 2 - r.left, (a.y + b.y) / 2 - r.top, abstand / letzterAbstand);
      }
      letzterAbstand = abstand;
    }
  });

  const loslassen = (e) => {
    const einzeln = zeiger.size === 1 && start;
    zeiger.delete(e.pointerId);
    if (zeiger.size < 2) letzterAbstand = 0;
    if (zeiger.size === 0) buehne.classList.remove('schiebt');
    if (!einzeln || bewegt >= 6) { start = null; return; }
    tippen(start.ziel);
    start = null;
  };
  buehne.addEventListener('pointerup', loslassen);
  buehne.addEventListener('pointercancel', (e) => { zeiger.delete(e.pointerId); start = null; buehne.classList.remove('schiebt'); });

  const tippen = (ziel) => {
    const klapper = ziel.closest?.('[data-klappen]');
    if (klapper) {
      const id = klapper.dataset.klappen;
      offen.has(id) ? offen.delete(id) : offen.add(id);
      zeichne(true);
      return;
    }
    const knoten = ziel.closest?.('[data-knoten]');
    if (knoten) waehle(knoten.dataset.knoten);
  };

  buehne.addEventListener('dblclick', (e) => {
    const r = buehne.getBoundingClientRect();
    const eingepasst = Math.min(r.width / W, r.height / H);
    if (s > eingepasst * 1.05) passeEin();
    else zoomAuf(e.clientX - r.left, e.clientY - r.top, 1 / s);
  });

  // Tastatur: die Knoten sind echte Schaltflaechen, der Baum bedienbar ohne Maus.
  buehne.addEventListener('keydown', (e) => {
    const knoten = e.target.closest?.('[data-knoten]');
    if (!knoten) return;
    const id = knoten.dataset.knoten;
    fokusId = id;
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); waehle(id); }
    if (e.key === 'ArrowRight' && !offen.has(id)) { offen.add(id); zeichne(true); }
    if (e.key === 'ArrowLeft' && offen.has(id)) { offen.delete(id); zeichne(true); }
  });

  wurzel.querySelector('.mm-leiste').addEventListener('click', (e) => {
    const tun = e.target.closest('[data-tun]')?.dataset.tun;
    if (tun === 'rein') zoomAuf(...mitte(), 1.25);
    if (tun === 'raus') zoomAuf(...mitte(), 0.8);
    if (tun === 'passen') passeEin();
    if (tun === 'gross') grossUmschalten();
    if (tun === 'klappen') {
      const zu = flach.some(({ knoten }) => (knoten.kinder || []).length && !offen.has(knoten.id));
      offen.clear();
      if (zu) for (const { knoten } of flach) if ((knoten.kinder || []).length) offen.add(knoten.id);
      zeichne(true);
    }
  });

  tafel.addEventListener('click', (e) => {
    const marke = e.target.closest('[data-zeige]');
    if (!marke || !marke.dataset.zeige) return;
    // Der Weg zum Ziel wird aufgeklappt, sonst zeigt der Sprung ins Leere.
    const ziel = nachId.get(marke.dataset.zeige);
    for (const { knoten } of flach) {
      if (alleKnoten(knoten).some(({ knoten: k }) => k.id === ziel.id) && (knoten.kinder || []).length) offen.add(knoten.id);
    }
    waehle(ziel.id);
    zentriereAuf(ziel);
  });

  const zentriereAuf = (k) => {
    const r = buehne.getBoundingClientRect();
    tx = r.width / 2 - (k._x + B / 2) * s;
    ty = r.height / 2 - (k._y + k._h / 2) * s;
    male();
  };

  // --- Gross und wieder klein ---------------------------------------------

  const taste = (e) => {
    if (!wurzel.classList.contains('voll')) return;
    if (e.key === 'Escape') grossUmschalten();
    if (e.key === '+' || e.key === '=') zoomAuf(...mitte(), 1.25);
    if (e.key === '-') zoomAuf(...mitte(), 0.8);
    if (e.key === '0') passeEin();
  };

  function grossUmschalten() {
    const voll = wurzel.classList.toggle('voll');
    grossKnopf.textContent = voll ? '×' : '⤢';
    grossKnopf.setAttribute('aria-label', voll ? 'schließen' : 'groß ansehen');
    document.body.style.overflow = voll ? 'hidden' : '';
    requestAnimationFrame(passeEin);
  }
  document.addEventListener('keydown', taste);

  // Nach einer Drehung des Tablets stimmt der Ausschnitt sonst nicht mehr.
  // Nur bei echter Groeszenaenderung, sonst springt der Zoom beim Aufklappen.
  let letzte = '';
  new ResizeObserver(([e]) => {
    const jetzt = `${Math.round(e.contentRect.width)}x${Math.round(e.contentRect.height)}`;
    if (jetzt === letzte) return;
    letzte = jetzt;
    passeEin();
  }).observe(buehne);

  zeichne();
  zeigeTafel();
  return wurzel;
}

/**
 * Holt den Knotenbaum. Fehlerantworten kommen als Daten zurueck, nicht als
 * Ausnahme: Sie tragen ihre Begruendung und werden angezeigt (TB-8).
 */
export async function holeMindmap(kapitelId) {
  try {
    const antwort = await fetch(weg(`api/kapitel/${encodeURIComponent(kapitelId)}/mindmap`));
    return await antwort.json();
  } catch (fehler) {
    return { fehler: 'dienst_nicht_erreichbar', grund: String(fehler) };
  }
}
