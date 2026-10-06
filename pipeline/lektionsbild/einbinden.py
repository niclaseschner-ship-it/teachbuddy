"""Bindet ein fertiges Lektionsbild in die Bibliothek ein.

Je Lektion mit `<ARBEIT>/lektionsbild/<ID>/bild.png`:

1. `<WISSEN>/bilder/lektionen/<ID>.html` — das Bild als JPEG im Dokument. Die
   App bettet jedes Bild als eigenes Dokument ein (bildschau.js), also bekommt
   auch das gemalte eines, statt einen zweiten Anzeigeweg zu brauchen.
2. Im Kopf der Lektionsdatei: `bild`, `bild_breite`, `bild_hoehe`,
   `bild_titel`, `bild_belege`.

`bild_belege` bleibt leer: Ein gemaltes Bild traegt keine Beleg-ID (E-19d).
Die Belege stehen in der Uebersichtsfolie darunter.

    python -m pipeline.lektionsbild.einbinden [ID ...]
"""
from __future__ import annotations

import base64
import io
import sys
from pathlib import Path

from PIL import Image

import pfade
from bibliothek.lesen import lies_bibliothek

WISSEN = pfade.WISSEN
ARBEIT = pfade.ARBEIT / "lektionsbild"
ZIEL = WISSEN / "bilder" / "lektionen"

HTML = """<!doctype html>
<meta charset="utf-8">
<title>{titel}</title>
<style>html,body{{margin:0;background:#FAF7F0}}img{{display:block;width:{b}px;height:{h}px}}</style>
<img alt="{titel}" width="{b}" height="{h}" src="data:image/jpeg;base64,{daten}">
"""

FELDER = ("bild", "bild_breite", "bild_hoehe", "bild_titel", "bild_belege")


def _kopf_setzen(datei: Path, werte: dict[str, str]) -> None:
    zeilen = datei.read_text(encoding="utf-8").split("\n")
    assert zeilen[0] == "---", datei
    ende = zeilen.index("---", 1)
    kopf = [z for z in zeilen[1:ende] if z.split(":", 1)[0] not in FELDER]
    # vor `erzeugt:`, wo die alten Bilder ihre Felder auch haben
    pos = next((i for i, z in enumerate(kopf) if z.startswith("erzeugt:")), len(kopf))
    neu = [f"{k}: {v}" for k, v in werte.items()]
    kopf[pos:pos] = neu
    datei.write_text("\n".join(["---", *kopf, *zeilen[ende:]]), encoding="utf-8")


def einbinden(ids: list[str]) -> None:
    bib = lies_bibliothek(WISSEN)
    ZIEL.mkdir(parents=True, exist_ok=True)
    for lid in ids:
        png = ARBEIT / lid / "bild.png"
        if not png.is_file():
            print(f"{lid}: kein Bild, uebersprungen")
            continue
        l = bib.lektionen[lid]
        bild = Image.open(png).convert("RGB")
        b, h = bild.size
        puffer = io.BytesIO()
        bild.save(puffer, "JPEG", quality=86, optimize=True, progressive=True)
        titel = l.titel.replace('"', "&quot;").replace("<", "&lt;")
        html = ZIEL / f"{lid}.html"
        html.write_text(HTML.format(titel=titel, b=b, h=h,
                                    daten=base64.b64encode(puffer.getvalue()).decode()),
                        encoding="utf-8")
        _kopf_setzen(WISSEN / l.pfad, {
            "bild": str(html.relative_to(WISSEN)),
            "bild_breite": str(b),
            "bild_hoehe": str(h),
            "bild_titel": l.titel,
            "bild_belege": "[]",
        })
        print(f"{lid}: {b}x{h}, {html.stat().st_size // 1024} KB")


if __name__ == "__main__":
    ids = sys.argv[1:]
    if not ids:
        ids = sorted(p.name for p in ARBEIT.glob("L-*") if (p / "bild.png").is_file())
    einbinden(ids)
