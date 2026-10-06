// Der Abspieler — die Bedienlogik einer Lektion.
//
// Was er kann, und woher die Anforderung kommt:
//   Bild der Einheit, anklickbar          OBF-9, E-19
//   Kapitelmarken, anspringbar            POD-4
//   Abspieltempo, bleibt über Lektionen   OBF-10a
//   15 Sekunden vor und zurück            OBF-10b
//   Offline sichern                       APP-5
//   Zustand setzen und sehen              OBF-3
//   Weg zu Fragen, Nachbarlektionen       OBF-11, Navigation im Kapitel

import { ikon, lektionsWeg } from './huelle.js';
import { zustandVon, ZUSTAND_TEXT, SCHWELLE_GEHOERT } from './zustand.js';

export const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s) % 60).padStart(2, '0')}`;
const roh = (t) => String(t).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const tempoText = (t) => t.toFixed(2).replace(/0$/, '').replace('.', ',') + '×';

// Jede Einheit hat ein Bild — seit Vertrag v2 als Feld `bild` (R-7 beantwortet).
// Ausgeliefert ist bisher genau eine Datei (L-023, die Grafik aus Lauf E). Die
// übrigen Einheiten zeigen sie als Platzhalter und sagen das auch.
/** Wo die App liegt — direkt unter / oder hinter einem Proxy unter einem Unterpfad. */
const BASIS = new URL('./', import.meta.url);
const weg = (p) => new URL(String(p).replace(/^\/+/, ''), BASIS).pathname;
const ZOOM_HINWEIS = 'Zoomen mit Rad, Fingern oder + und −; Doppeltippen wechselt zwischen eingepasst und 1:1.';

// Aus der Lektion das Bild machen, das die Bildschau versteht.
export function bildVon(l) {
  // Seit 11.09.2026 liefert der Dienst das Bild je Lektion (`bild.url`).
  // Vorher war hier eine Datei fest verdrahtet, weil nur eine auslag.
  const b = l.bild;
  if (b?.url) {
    return {
      url: weg(b.url),
      breite: b.breite || 1600,
      hoehe: b.hoehe || 1000,
      titel: b.titel || 'Bild der Einheit',
      quelle: `Bild als HTML mit SVG (E-19), aus den Wissenseinheiten gebaut. ${ZOOM_HINWEIS}`,
    };
  }
  // Kein Bild: sagen statt zeigen. Ein fremdes Bild waere erfundener Inhalt.
  return null;
}

export function zustandMarke(l) {
  const z = zustandVon(l);
  return `<span class="zustand-marke z-${z}" id="zustand-marke">${ZUSTAND_TEXT[z]}</span>`;
}

export function abspielerHtml(L, { vorige, naechste, kapitel } = {}) {
  const marken = L.kapitelmarken || [];
  return `
  <div class="spieler">
    <div class="spieler-bild"></div>

    <div class="spieler-jetzt">
      <span class="jetzt-wort">jetzt</span>
      <span class="jetzt-marke" id="jetzt-marke">—</span>
    </div>

    <div class="transport">
      <div class="spur" id="spur" role="slider" tabindex="0"
           aria-label="Position in der Lektion" aria-valuemin="0" aria-valuemax="${L.dauer_sek}" aria-valuenow="0">
        <div class="spur-bahn"></div>
        <div class="spur-fuell" id="fuell"></div>
        ${marken.map((m) => `<div class="spur-kerbe" style="left:${(m.sek / L.dauer_sek) * 100}%" title="${roh(m.titel)}"></div>`).join('')}
        <div class="spur-griff" id="griff"></div>
      </div>
      <div class="zeiten"><span id="jetzt">0:00</span><span id="rest">${mmss(L.dauer_sek)}</span></div>
    </div>

    <div class="knoepfe">
      <button class="rund sprung" data-spring="-15" aria-label="15 Sekunden zurück">
        <svg viewBox="0 0 20 20"><path d="M12 4L6 10l6 6M17 4l-6 6 6 6"/></svg><b>15</b>
      </button>
      <button class="rund gross" id="abspielen" aria-label="abspielen">${ikon.play}</button>
      <button class="rund sprung" data-spring="15" aria-label="15 Sekunden vor">
        <b>15</b><svg viewBox="0 0 20 20"><path d="M8 4l6 6-6 6M3 4l6 6-6 6"/></svg>
      </button>
      <button class="rund tempo" id="tempo" aria-label="Abspieltempo wechseln">1,0×</button>
    </div>

    <div class="werkzeugzeile">
      <button class="wz" id="offline">
        <svg viewBox="0 0 16 16"><path d="M8 2v8M4.6 7L8 10.4 11.4 7M3 13h10"/></svg>
        <span>offline sichern</span>
      </button>
      <button class="wz" id="gehoert">
        <svg viewBox="0 0 16 16"><path d="M3 8.4l3 3L13 4.6"/></svg>
        <span>als gehört markieren</span>
      </button>
      <a class="wz" href="#fragen">
        <svg viewBox="0 0 16 16"><path d="M5.8 5.8a2.2 2.2 0 1 1 3 2.1c-.5.2-.8.7-.8 1.2v.4"/><circle cx="8" cy="12.4" r=".9" fill="currentColor" stroke="none"/></svg>
        <span>zu den Fragen</span>
      </a>
      <!-- OBF-19: Die Bewertung gehoert zur Folge, also in die Reihe der
           Handgriffe an der Folge. Rückmeldung: „mach neben die buttons offline zu
           den fragen einfach einen mit feedback." -->
      <button class="wz" id="rueckmeldung" data-rueckmeldung>
        ${ikon.sagen}
        <span>Feedback</span>
      </button>
    </div>

    <nav class="nachbarn">
      ${vorige
        ? `<a href="${lektionsWeg(vorige, kapitel)}" class="nachbar"><span class="pfeil">‹</span><span class="nachbar-text"><i>vorige</i>${roh(vorige.titel)}</span></a>`
        : '<span class="nachbar leer"></span>'}
      ${naechste
        ? `<a href="${lektionsWeg(naechste, kapitel)}" class="nachbar rechts"><span class="nachbar-text"><i>nächste</i>${roh(naechste.titel)}</span><span class="pfeil">›</span></a>`
        : '<span class="nachbar leer"></span>'}
    </nav>

    <div class="marken-kopf">Kapitelmarken <small>${marken.length}</small></div>
    <ul class="kmarken">
      ${marken.map((m) => `
        <li><button class="kmarke" data-sek="${m.sek}">
          <span class="kmarke-sek">${mmss(m.sek)}</span>
          <span class="kmarke-titel">${roh(m.titel)}</span>
        </button></li>`).join('')}
    </ul>
  </div>`;
}

export function abspielerStarten(L) {
  const $ = (s) => document.querySelector(s);
  const marken = L.kapitelmarken || [];

  // OBF-10a: das Tempo gilt über Lektionen hinweg. Hier hält das der
  // Browserspeicher; in der App geht es an `PUT /api/einstellungen`
  // (Vertrag v2, `_schreibwege` — R-15 beantwortet).
  const TEMPI = [1, 1.25, 1.5, 1.75, 2];
  let tempo = Number(localStorage.getItem('tb-tempo')) || 1;
  if (!TEMPI.includes(tempo)) tempo = 1;

  let pos = L.position_sek || 0;
  let laeuft = false, uhr = null;

  // Der Ton.
  //
  // **Genau EIN Audio-Element ueber die ganze Wiedergabe**: iOS-Safari gibt Ton
  // in einer PWA nur von dem Element aus, das urspruenglich per Nutzergeste
  // aktiviert wurde. Ein zweites, spaeter erzeugtes Element laeuft, bleibt aber
  // stumm. Deshalb wird hier keines getauscht.
  let ton = document.getElementById('tb-ton');
  if (!ton) {
    ton = document.createElement('audio');
    ton.id = 'tb-ton';
    ton.preload = 'metadata';
    // Ins Dokument, nicht nur als Objekt: Ein freischwebendes Audio-Element
    // verliert in manchen Browsern seine Ton-Autorisierung, und Betriebssystem-
    // Bedienelemente (Sperrbildschirm) finden es gar nicht erst.
    document.body.appendChild(ton);
  }
  if (L.audio_url) {
    const quelle = new URL(weg(L.audio_url), location.href).href;
    if (ton.src !== quelle) {
      ton.src = quelle;
      // Nach einem Quellenwechsel laedt das Element nicht von selbst neu.
      // Ohne `load()` bleibt `readyState` auf 0 und `play()` tut nichts —
      // ohne Fehler, was die Suche unangenehm macht.
      ton.load();
    }
  }
  ton.addEventListener('loadedmetadata', () => { if (pos > 0) ton.currentTime = pos; },
    { once: true });

  // Die Wahrheit ueber die Position ist `ton.currentTime`, nicht ein Zaehler.
  // Sonst laufen Anzeige und Ton auseinander, sobald der Browser puffert.
  const jetztPos = () => (ton.duration ? ton.currentTime : pos);
  // Zwei Achsen statt eines Leiterzustands (Vertrag v2, R-4). Der Abspieler
  // bewegt nur `gehoert_anteil`; `fragen` gehört dem Fragenblock.
  const stand = { gehoert_anteil: L.gehoert_anteil ?? 0, fragen: L.fragen ?? 'offen' };
  let vonHandGehoert = false;

  // **Der Fortschritt geht an den Server** (OBF-7). Bis zum 12.09.2026 bewegte der
  // Abspieler nur seinen eigenen Zustand; in der Übersicht blieb eine gehörte
  // Lektion deshalb „ungehört". Die Bedienung war gebaut, das Melden
  // war nie angeschlossen.
  //
  // Er liegt auf dem Server und nicht im Browser, damit das Telefon weiß, was auf
  // dem Laptop gehört wurde.
  let zuletztGemeldet = -1;
  function melde({ endgueltig = false } = {}) {
    const p = Math.max(0, Math.min(L.dauer_sek, jetztPos()));
    // Nicht bei jedem Tick schreiben: ein PUT je Sekunde wäre Lärm.
    if (!endgueltig && Math.abs(p - zuletztGemeldet) < 10) return;
    zuletztGemeldet = p;
    const körper = JSON.stringify({
      position_sek: vonHandGehoert ? L.dauer_sek : p,
      fragen: stand.fragen,
    });
    fetch(weg(`api/lektion/${encodeURIComponent(L.id)}/fortschritt`), {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: körper,
      // Hält die Anfrage am Leben, wenn die Seite gerade zugeht — sonst
      // verliert man genau die letzte Meldung, auf die es ankommt.
      keepalive: true,
    }).catch(() => { zuletztGemeldet = -1; });   // beim nächsten Mal erneut
  }

  const pause = '<svg viewBox="0 0 12 14"><rect x="0" y="0" width="4" height="14"/><rect x="8" y="0" width="4" height="14"/></svg>';

  function malZustand() {
    const z = zustandVon(stand);
    const m = $('#zustand-marke');
    if (m) { m.className = `zustand-marke z-${z}`; m.textContent = ZUSTAND_TEXT[z]; }
    const k = $('#gehoert');
    const gehoert = stand.gehoert_anteil >= SCHWELLE_GEHOERT;
    k.classList.toggle('an', gehoert);
    k.querySelector('span').textContent = gehoert ? 'als gehört markiert' : 'als gehört markieren';
  }

  function male() {
    pos = Math.max(0, Math.min(L.dauer_sek, jetztPos()));
    const anteil = (pos / L.dauer_sek) * 100;
    $('#fuell').style.width = anteil + '%';
    $('#griff').style.left = anteil + '%';
    $('#jetzt').textContent = mmss(pos);
    $('#spur').setAttribute('aria-valuenow', Math.round(pos));

    const rest = (L.dauer_sek - pos) / tempo;
    $('#rest').textContent = tempo === 1
      ? `noch ${mmss(rest)}`
      : `noch ${mmss(rest)} bei ${tempoText(tempo)}`;

    let i = -1;
    marken.forEach((m, k) => { if (pos >= m.sek) i = k; });
    $('#jetzt-marke').textContent = i >= 0 ? marken[i].titel : '—';
    document.querySelectorAll('.kmarke').forEach((el, k) => el.classList.toggle('jetzt', k === i));

    // Vertrag v2 beantwortet R-4: gehört ab 95 %, weil Outros übersprungen
    // werden. Die Ableitung steckt in zustand.js, hier wird nur die Achse
    // fortgeschrieben — und eine Hand-Markierung nicht wieder überschrieben.
    if (!vonHandGehoert) stand.gehoert_anteil = pos / L.dauer_sek;
    malZustand();
  }

  function malTempo() {
    const k = $('#tempo');
    k.textContent = tempoText(tempo);
    k.classList.toggle('schnell', tempo !== 1);
    k.title = `Abspieltempo ${k.textContent} — tippen wechselt`;
  }

  function schalten(an) {
    laeuft = an;
    $('#abspielen').innerHTML = an ? pause : ikon.play;
    $('#abspielen').setAttribute('aria-label', an ? 'anhalten' : 'abspielen');
    $('#abspielen').classList.toggle('laeuft', an);
    clearInterval(uhr);
    if (!an) { ton.pause(); return; }
    ton.playbackRate = tempo;
    // `play()` kann abgelehnt werden (Autoplay-Regeln, iOS). Dann sagen wir es,
    // statt einen Knopf zu zeigen, der nichts tut (TB-8).
    ton.play().catch((f) => {
      laeuft = false;
      $('#abspielen').innerHTML = ikon.play;
      $('#abspielen').classList.remove('laeuft');
      const m = $('#jetzt-titel');
      if (m) m.textContent = 'Ton blockiert: ' + (f.message || f.name);
    });
    // Nur noch Anzeige — die Zeit kommt vom Element, nicht von einem Zaehler.
    uhr = setInterval(male, 200);
  }

  function springeAuf(x) {
    const r = $('#spur').getBoundingClientRect();
    setzePos(((x - r.left) / r.width) * L.dauer_sek);
  }

  /** Eine Stelle fuer alle Sprunge — sonst laufen Ton und Anzeige auseinander. */
  function setzePos(neu) {
    pos = Math.max(0, Math.min(L.dauer_sek, neu));
    if (ton.duration) ton.currentTime = pos;
    male();
  }

  ton.addEventListener('ended', () => {
    pos = L.dauer_sek; stand.gehoert_anteil = 1;
    schalten(false); male(); malZustand(); melde({ endgueltig: true });
  });
  ton.addEventListener('pause', () => melde({ endgueltig: true }));
  // Während des Hörens alle zehn Sekunden, damit ein Absturz höchstens zehn
  // Sekunden kostet.
  ton.addEventListener('timeupdate', () => {
    stand.gehoert_anteil = L.dauer_sek ? jetztPos() / L.dauer_sek : 0;
    melde();
  });
  // Wegklicken, Telefon sperren, Tab wechseln: das ist der häufigste Ausgang.
  addEventListener('pagehide', () => melde({ endgueltig: true }));
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') melde({ endgueltig: true });
  });
  ton.addEventListener('error', () => {
    const m = $('#jetzt-titel');
    if (m) m.textContent = 'Tonspur nicht ladbar (Code ' + (ton.error?.code ?? '?') + ')';
  });

  $('#abspielen').addEventListener('click', () => schalten(!laeuft));
  $('#tempo').addEventListener('click', () => {
    tempo = TEMPI[(TEMPI.indexOf(tempo) + 1) % TEMPI.length];
    localStorage.setItem('tb-tempo', String(tempo));
    ton.playbackRate = tempo;
    malTempo();
    male();
  });
  document.querySelectorAll('[data-spring]').forEach((b) =>
    b.addEventListener('click', () => setzePos(jetztPos() + Number(b.dataset.spring))));
  document.querySelectorAll('.kmarke').forEach((b) =>
    b.addEventListener('click', () => { setzePos(Number(b.dataset.sek)); if (!laeuft) schalten(true); }));

  $('#spur').addEventListener('pointerdown', (e) => { springeAuf(e.clientX); $('#spur').setPointerCapture(e.pointerId); });
  $('#spur').addEventListener('pointermove', (e) => { if (e.buttons) springeAuf(e.clientX); });
  $('#spur').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') setzePos(jetztPos() + 15);
    if (e.key === 'ArrowLeft') setzePos(jetztPos() - 15);
  });

  // APP-5: erst geladen, dann im Zug nutzbar. Der Schalter sagt, was er sichert.
  $('#offline').addEventListener('click', () => {
    const k = $('#offline'), t = k.querySelector('span');
    if (k.classList.contains('an')) {
      k.classList.remove('an'); t.textContent = 'offline sichern';
      k.title = '';
      return;
    }
    k.classList.add('laedt'); t.textContent = 'wird gesichert…';
    setTimeout(() => {
      k.classList.remove('laedt'); k.classList.add('an');
      t.textContent = 'offline verfügbar';
      k.title = 'Ton, Bild, Folie und Fragen liegen im Gerät (APP-5). Der Diskussionspartner braucht weiterhin Verbindung.';
    }, 900);
  });

  $('#gehoert').addEventListener('click', () => {
    vonHandGehoert = stand.gehoert_anteil < SCHWELLE_GEHOERT;
    stand.gehoert_anteil = vonHandGehoert ? 1 : pos / L.dauer_sek;
    malZustand();
    melde({ endgueltig: true });
  });

  malTempo();
  male();
}
