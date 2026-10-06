// Das Sprachgespräch — der Ton hinter der Bedienung.
//
// **Warum der Browser direkt mit dem Anbieter spricht** (E-20a): Echtzeit-Audio
// über den Server zu leiten, fügte genau die Latenz hinzu, derentwegen der Server-Weg
// verworfen wurde. Der langlebige Schlüssel bleibt trotzdem auf dem Server — dieser
// Code sieht nur ein Token, das nach einer Minute verfällt.
//
// **Warum die Uhr mitläuft** (E-21): Es gibt keine Obergrenze. Der Nutzer entscheidet
// selbst, wann genug ist — dafür muss er es sehen. Die Sichtbarkeit ist damit
// die einzige Kostenkontrolle, nicht eine Zugabe.
//
// **Warum 15 Sekunden Stille die Sitzung schließen** (OBF-13c): Die Uhr läuft
// auch in Denkpausen. Abgefangen wird nicht der nachdenkende, sondern der
// abgelenkte Lernende — dort entstehen die Kosten, an die niemand denkt.
//
// **Warum der Browser die Mitschrift meldet**: Weil der Server nicht mithört. Aus
// E-20a folgt, dass die Tonspur ihn nie berührt — also ist dieser Code die
// einzige Stelle, an der überhaupt jemand mitschreiben kann. Bleibt die
// Meldung aus, hat der Partner beim nächsten Mal kein Gedächtnis.

const BASIS = new URL('./', import.meta.url);
const weg = (p) => new URL(String(p).replace(/^\/+/, ''), BASIS).pathname;

/** Wie lange Stille erlaubt ist, bevor die Sitzung sich schließt. */
export const STILLE_SEK = 15;

/** Wie lange eine verdeckte Seite offen bleibt, bevor sie ehrlich zumacht.
 *
 * Rückmeldung vom 14.09.2026: „aufgehängt, vielleicht weil das Handy in den
 * Sperrbildschirm ist?" Das stimmte, und der Code kannte den Fall gar
 * nicht — keine Zeile zu `visibilitychange`.
 *
 * Was beim Sperren passiert: Der AudioContext wird angehalten, der Messer
 * liefert Nullen, das zählt als Stille, und nach fünfzehn Sekunden schließt
 * die Sitzung. Beim Entsperren ist sie weg, ohne dass jemand sie beendet
 * hätte. Aus seiner Sicht: aufgehängt.
 *
 * **Stille und ein abgeschaltetes Mikrofon sind nicht dasselbe.** Das eine
 * heißt „er denkt nach oder ist fertig", das andere „wir wissen es nicht".
 * Auf Ungewissheit darf nicht dieselbe Antwort folgen wie auf Stille.
 *
 * Eine Minute, nicht fünfzehn Sekunden: Ein kurzer Blick auf eine
 * Benachrichtigung soll das Gespräch nicht kosten. Länger auch nicht, denn
 * die Sitzung kostet Geld je Minute (E-20c), und niemand sieht sie.
 */
export const HINTERGRUND_SEK = 60;

export class Gespraech extends EventTarget {
  constructor(kapitelId) {
    super();
    this.kapitelId = kapitelId;
    this.pc = null;
    this.strom = null;
    this.sitzungId = null;
    this.preisProMinute = 0;
    this.waehrung = 'USD';
    this.begonnen = 0;
    this.stilleAb = 0;
    this._wacht = null;
    this._mitschrift = [];     // noch nicht gemeldete Beiträge
    this._offeneRede = null;   // was der Partner gerade spricht
  }

  get sekunden() {
    return this.begonnen ? (Date.now() - this.begonnen) / 1000 : 0;
  }

  get kosten() {
    return (this.sekunden / 60) * this.preisProMinute;
  }

  _melde(art, feld = {}) {
    this.dispatchEvent(new CustomEvent(art, { detail: { gespraech: this, ...feld } }));
  }

  async starten() {
    // 1. Token vom Server. Er entscheidet bei jeder Anfrage, ob eine Sitzung aufgeht.
    // **Sagen, was wir können, bevor der Server Werkzeuge verspricht.** Der
    // Partner bekommt seine vier Werkzeuge nur, wenn jemand sie ausführt —
    // und das tun wir hier (E-20a). Am 14.09.2026 war der Server neu und diese
    // Datei alt (der Service Worker lässt einen neuen Mantel absichtlich
    // warten): Der Partner rief ein Werkzeug, niemand antwortete, und die
    // Sitzung schloss nach fünfzehn Sekunden Stille.
    //
    // Ein alter Browser schickt dieses Feld nicht, bekommt keine Werkzeuge
    // und führt ein ärmeres, aber laufendes Gespräch.
    const antwort = await fetch(weg(`api/kapitel/${encodeURIComponent(this.kapitelId)}/sprachsitzung`),
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ werkzeuge: true }),
      });
    const daten = await antwort.json();
    if (!antwort.ok || daten.fehler) {
      throw new Error(daten.grund || `Der Server antwortet mit ${antwort.status}`);
    }
    this.sitzungId = daten.sitzung_id;
    this.preisProMinute = daten.preis_pro_minute ?? 0;
    this.waehrung = daten.waehrung || 'USD';

    // 2. Mikrofon. Ohne Erlaubnis gibt es kein Gespräch — das sagen wir auch.
    try {
      this.strom = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (f) {
      await this._beenden(0);
      throw new Error('Ohne Mikrofon geht es nicht: ' + (f.message || f.name));
    }

    // 3. WebRTC direkt zum Anbieter.
    this.pc = new RTCPeerConnection();
    this.pc.addTrack(this.strom.getAudioTracks()[0], this.strom);

    // Das Antwort-Element gehoert ins Dokument. Ein freischwebendes wird vom
    // Browser eingesammelt, sobald keine Referenz mehr zaehlt — dann bricht
    // die Stimme nach wenigen Sekunden ab, ohne Fehlermeldung. Derselbe
    // Fehler wie beim Abspieler (HSP-22).
    let ton = document.getElementById('tb-gespraech-ton');
    if (!ton) {
      ton = document.createElement('audio');
      ton.id = 'tb-gespraech-ton';
      ton.autoplay = true;
      ton.setAttribute('playsinline', '');   // iOS oeffnet sonst den Vollbildspieler
      document.body.appendChild(ton);
    }
    this.pc.ontrack = (e) => {
      ton.srcObject = e.streams[0];
      ton.play().catch(() => { /* Autoplay-Regel; der Nutzer hat gerade getippt */ });
      // Auch die Stimme des Partners zaehlt gegen die Stille.
      this._fremderStrom = e.streams[0];
      if (this._ctx) this._stilleBeobachten(e.streams[0]);
    };
    this._ton = ton;

    // Bricht die Verbindung weg, sagen wir es — statt still zu verstummen.
    this.pc.onconnectionstatechange = () => {
      const z = this.pc?.connectionState;
      if (z === 'failed' || z === 'disconnected' || z === 'closed') {
        if (this.begonnen) this.beenden('verbindung:' + z);
      }
    };

    // Der Ereigniskanal muss **vor** dem Angebot offen sein, sonst steht er
    // nicht im SDP und der Anbieter schickt nichts.
    this.dk = this.pc.createDataChannel('oai-events');
    this.dk.addEventListener('message', (e) => this._ereignis(e.data));

    const angebot = await this.pc.createOffer();
    await this.pc.setLocalDescription(angebot);

    const sdp = await fetch(
      `${daten.verbindung}?model=${encodeURIComponent(daten.modell || 'gpt-realtime')}`,
      {
        method: 'POST',
        body: angebot.sdp,
        headers: { Authorization: `Bearer ${daten.token}`, 'Content-Type': 'application/sdp' },
      });
    if (!sdp.ok) {
      await this._beenden(0);
      throw new Error(`Der Anbieter lehnt die Verbindung ab (${sdp.status})`);
    }
    await this.pc.setRemoteDescription({ type: 'answer', sdp: await sdp.text() });

    this.begonnen = Date.now();
    this.stilleAb = Date.now();
    this._stilleBeobachten(this._fremderStrom);
    this._wacht = setInterval(() => this._takt(), 1000);

    // **Den Bildschirm anlassen.** Wer spricht, fasst das Telefon nicht an —
    // also greift die Bildschirmabschaltung mitten im Gespräch, das Gerät
    // sperrt, und alles Weitere ist nur noch Schadensbegrenzung. Rückmeldung am
    // 14.09.2026, nachdem das Verhalten danach schon ehrlich war: „Handy geht
    // immer noch aus."
    //
    // Das ist die Wurzel, nicht der Sperrbildschirm. Ein Gespräch ohne Hände
    // braucht einen Wake Lock, sonst arbeitet das Betriebssystem gegen es.
    await this._wachHalten();

    // Sperrbildschirm, Tabwechsel, App in den Hintergrund: derselbe Zustand.
    this._sichtbarkeit = () => {
      if (document.visibilityState === 'hidden') {
        this.verstecktAb = Date.now();
      } else {
        this.verstecktAb = null;
        // Die Zeit im Hintergrund war keine Stille — der Zähler fängt neu an.
        this.stilleAb = Date.now();
        this._ctx?.resume?.().catch(() => {});
        // **Ein Wake Lock überlebt das Verdecken nicht.** Der Browser gibt ihn
        // frei, sobald die Seite in den Hintergrund geht, und gibt ihn nicht
        // von selbst zurück. Wer ihn nicht neu anfordert, hat ihn genau einmal.
        this._wachHalten();
      }
    };
    document.addEventListener('visibilitychange', this._sichtbarkeit);
    this._melde('offen');
    return this;
  }

  /** Den Bildschirm anlassen, solange gesprochen wird.
   *
   * `navigator.wakeLock` gibt es nicht überall. Fehlt es, wird das **gesagt**
   * statt verschwiegen (TB-8): Dann muss der Mensch die Bildschirmsperre
   * seines Geräts selbst hochsetzen, und er kann das nur, wenn er es weiß.
   */
  async _wachHalten() {
    if (this._wach) return;
    if (!('wakeLock' in navigator)) {
      this._melde('wach', { moeglich: false });
      return;
    }
    try {
      this._wach = await navigator.wakeLock.request('screen');
      // Gibt das Gerät ihn von sich aus frei — Akku leer, Nutzer sperrt von
      // Hand —, merken wir uns das, damit der nächste Versuch greift. **Und
      // sagen es**: Eine Zeile, die „Bildschirm bleibt an“ behauptet, während
      // der Lock längst weg ist, ist schlimmer als gar keine Zeile.
      this._wach.addEventListener('release', () => {
        this._wach = null;
        if (this.begonnen) this._melde('wach', { moeglich: false, grund: 'freigegeben' });
      });
      this._melde('wach', { moeglich: true });
    } catch (f) {
      this._wach = null;
      this._melde('wach', { moeglich: false, grund: f.message });
    }
  }

  /** Lautstärke messen, um Stille von Sprechen zu unterscheiden.
   *
   * **Beide Richtungen zählen.** Wenn der Partner spricht, ist die Sitzung
   * nicht still — auch wenn der Lernende gerade zuhört. Am 11.09.2026 wurde
   * nur das Mikrofon gemessen, und die Sitzung schloss sich mitten im
   * Gespräch.
   *
   * **Der AudioContext muss geweckt werden.** Auf Android startet er
   * `suspended`; ein schlafender Analyser liefert nur Nullen, und dann gilt
   * alles als Stille. Das war der eigentliche Fehler.
   */
  _stilleBeobachten(fremderStrom) {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (!Ctx) { this._messen = null; return; }   // ohne Messung nicht abschalten
    // Kommt der Partnerstrom erst nach dem Start, wird hier ein zweites Mal
    // beobachtet. Der alte Kontext muss dann weg, sonst laufen zwei.
    this._ctx?.close().catch(() => {});
    const ctx = new Ctx();
    ctx.resume?.().catch(() => {});
    this._ctx = ctx;

    const bauMesser = (strom) => {
      if (!strom) return null;
      const messer = ctx.createAnalyser();
      messer.fftSize = 512;
      ctx.createMediaStreamSource(strom).connect(messer);
      return { messer, puffer: new Uint8Array(messer.frequencyBinCount) };
    };
    const kanaele = [bauMesser(this.strom), bauMesser(fremderStrom)].filter(Boolean);

    // Sicherheitsnetz: Misst gar nichts jemals etwas — kaputter Analyser,
    // schlafender Kontext, fremder Browser — dann wird NICHT abgeschaltet.
    // Eine Sitzung, die mitten im Satz zugeht, ist schlimmer als eine, die
    // ein paar Minuten zu lang offen steht.
    this._jeGemessen = false;

    this._messen = () => {
      if (ctx.state === 'suspended') ctx.resume?.().catch(() => {});
      for (const k of kanaele) {
        k.messer.getByteTimeDomainData(k.puffer);
        let summe = 0;
        for (const w of k.puffer) summe += Math.abs(w - 128);
        const pegel = summe / k.puffer.length;
        if (pegel > 0.4) this._jeGemessen = true;
        // Schwelle niedrig: Lieber einmal zu oft „da spricht jemand“ als eine
        // Sitzung, die dem Nachdenkenden davonläuft.
        if (pegel > 2) { this.stilleAb = Date.now(); return; }
      }
    };
  }

  /** Mitschrift aus den Ereignissen des Anbieters ziehen.
   *
   * Die Namen haben sich mit dem GA-Stand geändert
   * (`response.audio_transcript.done` → `response.output_audio_transcript.done`).
   * Deshalb wird auf die Endung geprüft und nicht auf den ganzen Namen: Ein
   * stummes Gedächtnis wäre schwer zu bemerken.
   */
  _ereignis(roh) {
    let e;
    try { e = JSON.parse(roh); } catch { return; }
    const art = String(e.type || '');

    if (art.endsWith('input_audio_transcription.completed')) {
      this._merke('lernender', e.transcript);
    } else if (art.endsWith('output_audio_transcript.done')
            || art === 'response.audio_transcript.done') {
      this._merke('partner', e.transcript);
    } else if (art === 'response.function_call_arguments.done') {
      this._werkzeug(e);
    }
  }

  /** Einen Werkzeugaufruf des Partners an den Server geben (DIS-24).
   *
   * Der Partner ruft, der Server antwortet, der Browser reicht durch. Er hält
   * die Audioverbindung ohnehin selbst (E-20a), also führt der Weg über ihn
   * — nicht, weil das schön wäre, sondern weil es der einzige ist.
   *
   * **Ein Fehler wird zurückgegeben, nicht verschluckt.** Bleibt die Antwort
   * aus, wartet der Partner mitten im Satz auf etwas, das nie kommt, und das
   * Gespräch verstummt. Lieber sagt er, dass das Nachsehen nicht ging
   * (TB-8).
   */
  async _werkzeug(e) {
    const rufId = e.call_id || e.item_id;
    if (!rufId) return;
    // **Warten ist keine Stille.** Während der Server arbeitet, sagt niemand
    // etwas — und die Abschaltung nach fünfzehn Sekunden Stille würde die
    // Sitzung genau dann schließen, wenn sie am nützlichsten ist. Der Zähler
    // wird deshalb offen gehalten, solange ein Aufruf läuft.
    this._werkzeugeOffen = (this._werkzeugeOffen || 0) + 1;
    this.stilleAb = Date.now();
    let ergebnis;
    try {
      let argumente = {};
      try { argumente = JSON.parse(e.arguments || '{}'); } catch { argumente = {}; }
      const antwort = await fetch(
        weg(`api/sitzung/${encodeURIComponent(this.sitzungId)}/werkzeug`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            werkzeug: e.name, argumente, kapitel: this.kapitelId,
          }),
        });
      ergebnis = antwort.ok
        ? await antwort.json()
        : { fehler: `pi_${antwort.status}`,
            hinweis: 'Der Server antwortet nicht. Sag das im Gespräch.' };
    } catch (f) {
      ergebnis = { fehler: 'pi_nicht_erreichbar',
                   hinweis: `Der Server ist nicht erreichbar (${f.message}).` };
    }
    this._werkzeugeOffen = Math.max(0, (this._werkzeugeOffen || 1) - 1);
    this.stilleAb = Date.now();
    this._melde('werkzeug', { name: e.name, ergebnis });
    this._senden({
      type: 'conversation.item.create',
      item: {
        type: 'function_call_output',
        call_id: rufId,
        output: JSON.stringify(ergebnis),
      },
    });
    // Ohne das bleibt das Ergebnis liegen und der Partner sagt nichts dazu.
    this._senden({ type: 'response.create' });
  }

  _senden(nachricht) {
    if (this.dk?.readyState !== 'open') return;
    this.dk.send(JSON.stringify(nachricht));
  }

  _merke(rolle, text) {
    const sauber = String(text ?? '').trim();
    if (!sauber) return;
    this._mitschrift.push({ rolle, text: sauber });
    this._melde('gesagt', { rolle, text: sauber });
    // In Schüben melden, nicht erst am Ende: Ein abgestürzter Browser oder ein
    // leerer Akku darf das Gespräch nicht mitnehmen.
    if (this._mitschrift.length >= 4) this._mitschriftMelden();
  }

  async _mitschriftMelden() {
    if (!this.sitzungId || !this._mitschrift.length) return;
    const schub = this._mitschrift.splice(0, this._mitschrift.length);
    try {
      await fetch(weg(`api/sitzung/${encodeURIComponent(this.sitzungId)}/mitschrift`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kapitel_id: this.kapitelId, beitraege: schub }),
      });
    } catch {
      // Zurück in die Schlange, statt sie wegzuwerfen.
      this._mitschrift.unshift(...schub);
    }
  }

  _takt() {
    this._messen?.();
    const still = (Date.now() - this.stilleAb) / 1000;
    const misst = Boolean(this._messen) && this._jeGemessen;

    // **Verdeckt heißt nicht still.** Solange die Seite im Hintergrund liegt,
    // hält der Browser den AudioContext an; der Messer liest dann Nullen, und
    // die sind keine Aussage über das Mikrofon. Deshalb zählt diese Zeit
    // nicht gegen die Stille — sie zählt gegen eine eigene Uhr.
    //
    // Manche Browser lassen ein laufendes Gespräch mit ausgeschaltetem
    // Bildschirm weiterlaufen. Wird also weiter gemessen, bleibt alles wie
    // sonst: Das Telefon am Ohr ist ein gültiger Fall.
    if (this.verstecktAb) {
      const verdeckt = (Date.now() - this.verstecktAb) / 1000;
      // **Die Frage ist nicht, was der AudioContext über sich sagt, sondern
      // ob noch etwas ankommt.** `_messen` setzt `stilleAb` auf jetzt, sobald
      // es Ton hört. Liegt der letzte Ton vor dem Verdecken, ist seither
      // nichts mehr gekommen — dann sind wir taub, nicht still.
      //
      // Kommt weiter Ton, ist das Gespräch am Leben: Telefon am Ohr,
      // Bildschirm aus. Dann wird auch die Stilleuhr nicht angewandt, denn
      // wer den Bildschirm ausschaltet, denkt vielleicht gerade nach.
      const seitTon = (Date.now() - this.stilleAb) / 1000;
      const taub = seitTon >= verdeckt;
      this._melde('takt', { stilleSek: 0, misst, verdecktSek: verdeckt });
      if (taub && verdeckt >= HINTERGRUND_SEK) this.beenden('hintergrund');
      return;
    }

    this._melde('takt', { stilleSek: still, misst });
    // Ohne funktionierende Messung wird nicht abgeschaltet (siehe oben),
    // und nicht, solange ein Werkzeug noch arbeitet.
    if (misst && !this._werkzeugeOffen && still >= STILLE_SEK) this.beenden('stille');
  }

  async beenden(grund = 'nutzer') {
    const sek = this.sekunden;
    await this._beenden(sek);
    this._melde('zu', { grund, sekunden: sek });
  }

  async _beenden(sekunden) {
    // Vor allem anderen: Die Sitzungsnummer wird hier unten gelöscht, und ohne
    // sie hat die Mitschrift keine Adresse mehr.
    await this._mitschriftMelden();
    clearInterval(this._wacht); this._wacht = null;
    this._wach?.release?.().catch(() => {}); this._wach = null;
    if (this._sichtbarkeit) {
      document.removeEventListener('visibilitychange', this._sichtbarkeit);
      this._sichtbarkeit = null;
    }
    this.verstecktAb = null;
    this.dk?.close?.(); this.dk = null;
    this.pc?.close(); this.pc = null;
    this.strom?.getTracks().forEach((t) => t.stop()); this.strom = null;
    this._ctx?.close().catch(() => {}); this._ctx = null;
    if (this._ton) { this._ton.srcObject = null; this._ton = null; }  // bleibt im DOM
    this.begonnen = 0;
    if (this.sitzungId) {
      // Gemeldet wird die **offene Verbindung**, nicht die Sprechzeit (E-20c).
      // Ohne diese Meldung fehlt die Sitzung in /api/kosten.
      try {
        await fetch(weg(`api/sitzung/${encodeURIComponent(this.sitzungId)}/ende`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ sekunden }),
        });
      } catch { /* Der Server ist weg — die Sitzung ist trotzdem zu. */ }
      this.sitzungId = null;
    }
  }
}

export const geld = (betrag, waehrung) =>
  `${betrag.toFixed(2).replace('.', ',')} ${waehrung === 'USD' ? '$' : waehrung}`;
