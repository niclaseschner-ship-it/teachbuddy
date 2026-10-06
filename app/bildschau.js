// Bildschau — die große, zoombare Ansicht für jedes Bild.
//
// Ein Bild ist bei TeachBuddy ein eigenständiges HTML-Dokument mit einem SVG
// darin (E-19: Grafiken entstehen als Code). Deshalb wird es als Dokument
// eingebettet und nicht in die Seite hineinkopiert: Die Grafik bringt eigene
// CSS-Klassen mit, die „.h1", „.body", „.cap" heißen und in jeder Seite
// kollidieren würden. Weil ein SVG eine viewBox hat, bleibt jeder Zoomschritt
// scharf — es wird neu gezeichnet, nicht hochgerechnet.
//
// Dasselbe Modul trägt später die Mindmap. Es weiß nichts über Lektionen.

const grenze = (w, min, max) => Math.min(max, Math.max(min, w));

export function bildRahmen({ url, breite, hoehe }) {
  const f = document.createElement('iframe');
  f.src = url;
  f.width = breite;
  f.height = hoehe;
  f.setAttribute('scrolling', 'no');
  f.setAttribute('loading', 'lazy');
  f.setAttribute('tabindex', '-1');
  f.setAttribute('aria-hidden', 'true');
  Object.assign(f.style, {
    width: breite + 'px', height: hoehe + 'px', border: '0',
    display: 'block', pointerEvents: 'none', background: '#fff',
  });
  return f;
}

export function bildschau({ url, breite, hoehe, titel, quelle }) {
  const schau = document.createElement('div');
  schau.className = 'bildschau';
  schau.innerHTML = `
    <div class="bs-leiste">
      <div class="bs-titel">${titel || 'Bild'}</div>
      <div class="bs-knoepfe">
        <button class="bs-k" data-tun="raus" aria-label="kleiner">−</button>
        <button class="bs-k bs-stufe" data-tun="passen">100 %</button>
        <button class="bs-k" data-tun="rein" aria-label="größer">+</button>
        <button class="bs-k bs-zu" data-tun="zu" aria-label="schließen">×</button>
      </div>
    </div>
    <div class="bs-buehne"><div class="bs-halter"></div></div>
    ${quelle ? `<div class="bs-fuss">${quelle}</div>` : ''}`;

  const buehne = schau.querySelector('.bs-buehne');
  const halter = schau.querySelector('.bs-halter');
  const stufe = schau.querySelector('.bs-stufe');
  halter.appendChild(bildRahmen({ url, breite, hoehe }));

  let s = 1, tx = 0, ty = 0, minS = 0.1;

  const male = () => {
    halter.style.transform = `translate(${tx}px, ${ty}px) scale(${s})`;
    stufe.textContent = Math.round(s * 100) + ' %';
  };

  const einpassen = () => {
    const r = buehne.getBoundingClientRect();
    s = Math.min(r.width / breite, r.height / hoehe);
    minS = s * 0.5;
    tx = (r.width - breite * s) / 2;
    ty = (r.height - hoehe * s) / 2;
    male();
  };

  // Zoom um einen Punkt: was unter dem Finger liegt, bleibt unter dem Finger.
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

  // Ein Zeiger schiebt, zwei Zeiger zoomen. Pointer Events, damit Maus,
  // Finger und Stift denselben Weg nehmen.
  const zeiger = new Map();
  let letzterAbstand = 0;

  buehne.addEventListener('pointerdown', (e) => {
    buehne.setPointerCapture(e.pointerId);
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });
    letzterAbstand = 0;
    buehne.classList.add('schiebt');
  });

  buehne.addEventListener('pointermove', (e) => {
    if (!zeiger.has(e.pointerId)) return;
    const alt = zeiger.get(e.pointerId);
    zeiger.set(e.pointerId, { x: e.clientX, y: e.clientY });

    if (zeiger.size === 1) {
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
    zeiger.delete(e.pointerId);
    if (zeiger.size < 2) letzterAbstand = 0;
    if (zeiger.size === 0) buehne.classList.remove('schiebt');
  };
  buehne.addEventListener('pointerup', loslassen);
  buehne.addEventListener('pointercancel', loslassen);

  // Doppeltippen springt zwischen eingepasst und 1:1.
  buehne.addEventListener('dblclick', (e) => {
    const r = buehne.getBoundingClientRect();
    const eingepasst = Math.min(r.width / breite, r.height / hoehe);
    if (s > eingepasst * 1.05) einpassen();
    else zoomAuf(e.clientX - r.left, e.clientY - r.top, 1 / s);
  });

  const zu = () => {
    document.removeEventListener('keydown', taste);
    window.removeEventListener('resize', beiGroesse);
    schau.remove();
    document.body.style.overflow = '';
  };

  const taste = (e) => {
    if (e.key === 'Escape') zu();
    if (e.key === '+' || e.key === '=') zoomAuf(...mitte(), 1.25);
    if (e.key === '-') zoomAuf(...mitte(), 0.8);
    if (e.key === '0') einpassen();
  };

  // Nach einer Drehung des Tablets stimmt der Ausschnitt sonst nicht mehr.
  let ruht;
  const beiGroesse = () => { clearTimeout(ruht); ruht = setTimeout(einpassen, 120); };

  schau.querySelector('.bs-knoepfe').addEventListener('click', (e) => {
    const tun = e.target.dataset.tun;
    if (tun === 'zu') zu();
    if (tun === 'passen') einpassen();
    if (tun === 'rein') zoomAuf(...mitte(), 1.25);
    if (tun === 'raus') zoomAuf(...mitte(), 0.8);
  });
  schau.addEventListener('click', (e) => { if (e.target === schau) zu(); });
  document.addEventListener('keydown', taste);
  window.addEventListener('resize', beiGroesse);

  document.body.style.overflow = 'hidden';
  document.body.appendChild(schau);
  einpassen();
  schau.querySelector('.bs-zu').focus();
  return zu;
}

// Macht etwas anklickbar, das die Bildschau öffnet.
export function machKlickbar(knopf, bild) {
  knopf.addEventListener('click', () => bildschau(bild));
}

// Die Bild-Karte: der eine Baustein für jedes Bild in der App. Das Lektionsbild
// nimmt denselben Weg wie die Mindmap des Kapitels, weil beide dieselbe Form
// haben — ein eigenständiges HTML-Dokument mit einem SVG darin (E-19).
// Wer ein drittes Bild einführt, ändert hier nichts.
export function bildKarte(bild, { lupe = 'groß ansehen', maxHoehe = 0 } = {}) {
  const knopf = document.createElement('button');
  knopf.className = 'bild-karte';
  knopf.type = 'button';
  knopf.setAttribute('aria-label', `${bild.titel || 'Bild'} groß anzeigen`);
  knopf.innerHTML = `
    <span class="bild-buehne"><span class="bild-halter"></span></span>
    <span class="bild-lupe">
      <svg viewBox="0 0 16 16"><circle cx="7" cy="7" r="4.6"/><path d="M10.4 10.4L14 14M7 5.2v3.6M5.2 7h3.6"/></svg>
      ${lupe}
    </span>`;

  const buehne = knopf.querySelector('.bild-buehne');
  const halter = knopf.querySelector('.bild-halter');

  // **Der Rahmen entsteht erst, wenn die Karte ins Bild kommt.**
  // Ein Bild ist ein eigenständiges HTML-Dokument mit SVG darin; die Mindmap
  // zu K-01 hat 107 KB. Sie beim Seitenaufbau zu laden macht die Seite auf
  // dem Telefon träge, obwohl sie oft gar nicht angesehen wird (13.09.2026).
  // `loading="lazy"` allein genügt nicht: Es greift bei Rahmen erst spät und
  // nicht überall.
  let geladen = false;
  const laden = () => {
    if (geladen) return;
    geladen = true;
    halter.appendChild(bildRahmen(bild));
    mass();
  };
  if ('IntersectionObserver' in window) {
    const wache = new IntersectionObserver((eintraege) => {
      if (eintraege.some((e) => e.isIntersecting)) { wache.disconnect(); laden(); }
    }, { rootMargin: '300px' });
    wache.observe(buehne);
  } else {
    laden();
  }

  // Das Seitenverhältnis kommt aus den Maßen, nicht aus dem geladenen Bild —
  // sonst springt das Layout, sobald das Dokument fertig ist.
  buehne.style.aspectRatio = `${bild.breite} / ${bild.hoehe}`;
  if (maxHoehe) buehne.style.maxHeight = maxHoehe + 'px';

  const mass = () => {
    const breit = buehne.getBoundingClientRect().width;
    if (!breit) return;
    halter.style.transform = `scale(${breit / bild.breite})`;
    // Wird die Vorschau durch maxHoehe beschnitten, bekommt sie eine Kante.
    const voll = breit * (bild.hoehe / bild.breite);
    knopf.classList.toggle('beschnitten', Boolean(maxHoehe) && voll > maxHoehe + 1);
  };
  new ResizeObserver(mass).observe(buehne);

  machKlickbar(knopf, bild);
  return knopf;
}
