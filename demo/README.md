# Die Bibliothek

Hier liegt, **was gilt** und **woher es stammt**. Die App liest nur von hier;
`bibliothek/` baut daraus einen Index (`python -m bibliothek.index`).

## Die eine Regel

> **Was hier liegt, hat ein Mensch freigegeben.**

Agenten schlagen vor, indem sie Dateien schreiben. Ein `git diff` zeigt
zeilengenau, was vorgeschlagen wird. Freigabe ist ein Commit, Ablehnung ist
`git checkout .` (BIB-16, BIB-18a). Deshalb liegt die Bibliothek in Dateien
und nicht in einer Datenbank ([`decisions/E-9.md`](../decisions/E-9.md)).

## Aufbau

```
pfade/P-01.md                 ein Lernpfad: Ziel, Kapitel, Tiefenstufen
kapitel/K-01.md               ein Kapitel: Lektionen und Material
mindmap/K-01.md               die Gliederung des Kapitels (Achsen, Unterachsen)
pruefung/K-01-1.md            Befunde der unabhängigen Gegenprobe
eingang/A-002/                ein Rechercheertrag
  quellen/Q-0007/
    quelle.md                 Titel, Urheber, Fundort, Abruf, Lizenz
    versionen/V-….md          der gesicherte Wortlaut (nur bei freier Lizenz)
    fundstellen.md            F-0007-01 … wörtliches Zitat + Stelle
  belege/B-0007-01.md         die aus einer Fundstelle abgeleitete Aussage
eingang/M-002/                ein Modellierungsertrag
  einheiten/WE-0042.md        ein lernbarer Baustein mit Belegen und Kanten
  lektionen/L-A01.md          eine Lektion: Einheiten, Audio, Kapitelmarken, Bild
  luecken.md                  was das Material nicht trägt
bilder/lektionen/L-A01.html   das Lektionsbild
audio/L-A01.mp3               die Folge (nicht im Git, `python start.py --audio`)
```

**Fundstelle und Beleg sind getrennt.** Die Fundstelle gehört der Quelle
(dort steht dieser Wortlaut), der Beleg ist die Deutung (das folgt daraus).
Wer beides vermischt, kann später einen Deutungsfehler nicht mehr von einem
Zitierfehler unterscheiden.

Das vollständige Modell steht in [`specs/bibliothek.md`](../specs/bibliothek.md),
die Lizenz der Inhalte in [`LIZENZ.md`](LIZENZ.md).
