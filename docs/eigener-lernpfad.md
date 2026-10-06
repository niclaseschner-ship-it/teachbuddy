# Einen eigenen Lernpfad bauen

TeachBuddy baut Lernpfade mit einer Warteschlange aus Agenten. Du legst fest,
**was** gelernt werden soll; die Agenten recherchieren, modellieren, prüfen,
schreiben und vertonen. **Freigegeben wird nichts von selbst:** Alles landet als
Änderung in deiner Bibliothek, und erst dein Commit macht es gültig.

> Schneller geht es mit einem Coding-Agenten: Öffne das Repo in Claude Code
> oder Codex und sag „Ich will einen eigenen Lernpfad". Der Skill
> (`.claude/skills/teachbuddy/SKILL.md`) führt durch alle Schritte unten.

## Was du brauchst

| | wofür |
|---|---|
| [Claude Code](https://claude.com/claude-code) (`claude`, angemeldet) | Recherche, Wissenseinheiten, Mindmap-Analyse |
| [Codex CLI](https://github.com/openai/codex) (`codex`, angemeldet) | Gegenprobe, Podcast-Skript, Lektionsbild |
| Azure OpenAI mit einem TTS-Deployment | Vertonung (`TEACHBUDDY_AZURE_OPENAI_*` in `.env`) |
| `ffmpeg` | Zusammenfügen der Folgen |
| `pip install -e ".[studio]"` | `openai` und `pillow` |

Beide CLIs laufen über ihre Abos, nicht über API-Schlüssel (TB-5). Ein
Kapitel kostet einiges an Kontingent: Rechne mit mehreren Stunden und einem
Großteil eines Tageskontingents. Deshalb arbeitet die Warteschlange
standardmäßig nur von 21 bis 8 Uhr (`TEACHBUDDY_FENSTER`).

## 1. Die eigene Bibliothek anlegen

```bash
python -m bibliothek.anlegen ~/teachbuddy-bibliothek --env
```

Sie liegt außerhalb des TeachBuddy-Repos und ist ein eigenes Git-Repo — so
kommen Updates von TeachBuddy und deine Inhalte sich nicht in die Quere. Mit
`--env` steht sie in `.env`, und App wie Pipeline arbeiten ab jetzt mit ihr.
Die Pfade unten sind relativ zu dieser Bibliothek.

## 2. Den Lernpfad beschreiben

Lege `pfade/P-01.md` an. Wichtig sind das Ziel und je Lektion ein
Abschnitt mit einer kurzen Beschreibung, was dort gelernt werden soll —
daran orientiert sich die Recherche.

```markdown
---
id: P-01
titel: Photovoltaik fürs eigene Dach
kurzfassung: >
  Von der Dachfläche bis zur Abrechnung: was man wissen muss, um eine
  Anlage zu planen und Angebote zu vergleichen.
reihenfolge: 1
status: entwurf
sprache: de
zielprofil: >
  Angebote verstehen und vergleichen können. Kein Elektriker-Wissen.
---

# Photovoltaik fürs eigene Dach

## Abschnitte

### V1 — Was ein Modul leistet
Nennleistung, Wirkungsgrad, Ausrichtung — und warum kWp nicht kWh ist.

### V2 — Speicher: wann er sich rechnet
Eigenverbrauchsquote, Zyklen, Kosten pro gespeicherter kWh.
```

Wie ein Lernpfad gut geschnitten wird, steht in
[`auftraege/curriculum.md`](../auftraege/curriculum.md). Du kannst diesen
Auftrag auch einem Agenten geben und dir einen Entwurf schreiben lassen.

## 3. Das Kapitel anlegen

`kapitel/K-01.md` fasst Lektionen zu einem Kapitel zusammen — mit einer
Mindmap und einem Gesprächspartner. Die Kürzel unter `lektionen` sind die
Abschnitte aus dem Lernpfad.

```markdown
---
id: K-01
pfad: P-01
nummer: 1
welle: 1
tiefenstufe: Überblick
titel: Photovoltaik — die Grundlagen
kurzfassung: >
  Was eine Anlage leistet und was sie kostet.
lektionen: [V1, V2]
---
```

## 4. Die Warteschlange laufen lassen

```bash
python -m pipeline.nachtlauf --plan          # was anstünde
TEACHBUDDY_FENSTER=0-24 python -m pipeline.nachtlauf --nur K-01
```

Sie arbeitet ein Kapitel vollständig ab, ein Schritt nach dem anderen:

1. **Recherche** — Quellen mit Lizenz, Fundstellen mit Zitat, Belege
2. **Wissen** — Wissenseinheiten und Lektionen; was das Material nicht trägt,
   steht in `luecken.md` statt erfunden zu werden
3. **Gegenprobe** — das jeweils andere Modell prüft jede Aussage gegen ihren Beleg
4. **Podcast** — Skript, Vertonung, Kapitelmarken, Eintrag in die Lektion
5. **Mindmap-Analyse** — die Gliederung des Kapitels

Nach jedem gelungenen Schritt committet sie den Ertrag in der Bibliothek — als
Sicherung, nicht als Freigabe. Ist das Abo-Kontingent erschöpft, wartet sie
bis zur gemeldeten Uhrzeit und macht dann weiter. Protokolle liegen unter
`arbeit/pipeline/`.

## 5. Lektionsbilder malen

```bash
pipeline/lektionsbild/alle.sh                # alle Lektionen ohne Bild
pipeline/lektionsbild/bauen.sh V1            # oder eine einzelne
```

Je Bild etwa drei Minuten. **Sieh dir jedes Bild an**, bevor du es
veröffentlichst: Gelegentlich rutscht ein Schreibfehler oder ein dunkler
Schleier über dem Titel durch. Ein misslungenes Bild malst du mit `bauen.sh`
einfach neu.

## 6. Prüfen und freigeben

```bash
cd ~/teachbuddy-bibliothek
git diff                          # was vorgeschlagen ist
cat pruefung/K-01-*.md            # was die Gegenprobe beanstandet
python -m bibliothek.befunde      # aus dem TeachBuddy-Repo: was am Material auffällt
git commit -am "P-01: Photovoltaik freigegeben"
```

Was du nicht willst, verwirfst du mit `git checkout <datei>`.

Die Beanstandungen der Gegenprobe arbeitest du ein, bevor du freigibst: an der
Quelle nachprüfen, Beleg und Wissenseinheit korrigieren, betroffene Folge und
Bild neu bauen. Wie das aussieht, zeigt `demo/pruefung/K-03-1.md` unten unter
„Nachgebessert". Danach `python start.py --neu`.
