"""Das Material einer Lektion für den Bildauftrag, als Markdown.

    python -m pipeline.lektionsbild.material L-S2
    python -m pipeline.lektionsbild.material --ohne-bild   # Lektionen ohne Bild
"""
import sys

import pfade
from bibliothek.lesen import lies_bibliothek


def main(argv: list[str]) -> None:
    b = lies_bibliothek(pfade.WISSEN)
    if argv[:1] == ["--ohne-bild"]:
        print(" ".join(sorted(l.id for l in b.lektionen.values() if not l.bild)))
        return
    l = b.lektionen[argv[0]]
    print(f"# {l.titel}\n\nLektion {l.id}, Kapitel {l.kapitel}.\n")
    for wid in l.wissenseinheiten:
        w = b.einheiten[wid]
        print(f"## {w.stichwort} — {w.titel}\n\n{w.kurzfassung}\n\n{w.inhalt}\n")


if __name__ == "__main__":
    main(sys.argv[1:])
