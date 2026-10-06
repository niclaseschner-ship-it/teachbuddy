// Die Anzeige-Zustände einer Lektion, abgeleitet nach `_zustandsregel` aus
// Datenvertrag v2 (R-4).
//
// Der Vertrag führt seit v2 **zwei unabhängige Achsen** statt eines Leiter-
// zustands: `gehoert_anteil` (0..1) und `fragen` (offen | teilweise | fertig).
// Das ist die richtige Form, weil OBF-3 sagt, konsumiert und geprüft seien
// verschiedene Dinge — die Anzeige fasst sie nur zusammen.

export const SCHWELLE_GEHOERT = 0.95;   // Outros werden übersprungen
export const SCHWELLE_ANGEFANGEN = 0.02;

export const ZUSTAND_TEXT = {
  ungehoert: 'ungehört',
  angefangen: 'angefangen',
  gehoert: 'gehört',
  fragen_beantwortet: 'Fragen beantwortet',
};

export function zustandVon(l) {
  const anteil = l.gehoert_anteil ?? 0;
  const fragen = l.fragen ?? 'offen';
  if (fragen === 'fertig') return 'fragen_beantwortet';
  if (anteil >= SCHWELLE_GEHOERT) return 'gehoert';
  if (anteil >= SCHWELLE_ANGEFANGEN) return 'angefangen';
  // Lücke in der Regel: „ungehört" verlangt fragen == offen, sagt aber nicht,
  // was bei fragen == teilweise und kaum gehört gilt. Wer die Fragen angefangen
  // hat, hat angefangen.
  return fragen === 'teilweise' ? 'angefangen' : 'ungehoert';
}

export const istGehoert = (l) => (l.gehoert_anteil ?? 0) >= SCHWELLE_GEHOERT;
export const istGeprueft = (l) => l.fragen === 'fertig';

// Fortschritt eines Kapitels — die Aggregate sind in v2 aus dem Vertrag
// geflogen (R-1, R-2), weil sie ableitbar sind und schon im Mock auseinander-
// liefen. Hier ist die eine Stelle, die sie berechnet.
export function fortschritt(k) {
  // **Geplante Lektionen zählen nicht mit.** Ein Kapitel hat dreizehn
  // Lektionen, gebaut ist eine. „0 von 13 gehört" wäre keine Untertreibung,
  // sondern falsch: Zwölf davon gibt es als Folge gar nicht, also kann man
  // sie nicht gehört haben. Sie stehen getrennt als `geplant`.
  // Ohne Folge kann man nichts gehört haben — auch wenn das Wissen daliegt.
  const gebaut = k.lektionen.filter((l) => !l.geplant && l.hat_ton !== false);
  return {
    gesamt: gebaut.length,
    geplant: k.lektionen.length - gebaut.length,
    gehoert: gebaut.filter(istGehoert).length,
    geprueft: gebaut.filter(istGeprueft).length,
    offenSek: gebaut
      .filter((l) => !istGehoert(l))
      .reduce((s, l) => s + ((l.dauer_sek || 0) - (l.position_sek || 0)), 0),
  };
}
