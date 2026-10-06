"""Baut die App-Icons.

**Warum von Hand und nicht aus einer Bilddatei:** Ein Icon ist Struktur, keine
Fotografie — dieselbe Begründung wie E-19 für die Lerngrafiken. So liegt es
versioniert im Repo, lässt sich in einer Zeile ändern und sieht in jeder Größe
gleich aus.

Das Zeichen: ein **Sprechbogen über einer Grundlinie**. Der Bogen ist der
Podcast und das Gespräch, die Linie darunter der Beleg, auf dem beides steht —
TB-1 als Bild. Kein Buchstabensalat, auf 48 Pixeln noch erkennbar.

Farben aus `app/stil.css` (helles Thema), damit das Symbol auf dem Startbildschirm
zur App gehört und nicht zu einem fremden Programm:

    Grund   #f7f6f3   --bg
    Bogen   #b57722   --hoeren
    Beleg   #2f8f6d   --geprueft
    Linie   #1c1f24   --text

Aufruf::

    python3 app/icons/_bauen.py
"""

import struct
import zlib
from pathlib import Path

HIER = Path(__file__).resolve().parent

GRUND = (0xF7, 0xF6, 0xF3)
BOGEN = (0xB5, 0x77, 0x22)
BELEG = (0x2F, 0x8F, 0x6D)
TEXT = (0x1C, 0x1F, 0x24)


def _mische(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def _zeichne(kante: int, maskierbar: bool) -> bytes:
    """Ein Bild als Pixelraster. Kein Zeichenwerkzeug noetig, kein Fremdpaket."""
    # Maskierbare Icons werden von Android beschnitten: Alles Wichtige muss in
    # den inneren 80 % liegen, sonst schneidet das System das Zeichen an.
    rand = 0.20 if maskierbar else 0.13
    mitte = kante / 2
    r_aussen = kante * (0.5 - rand)

    zeilen = bytearray()
    for y in range(kante):
        zeilen.append(0)  # Filtertyp 0 je Zeile
        for x in range(kante):
            dx, dy = (x - mitte) / r_aussen, (y - mitte) / r_aussen
            farbe = GRUND

            # Sprechbogen: ein offener Ring, unten ausgespart.
            d = (dx * dx + dy * dy) ** 0.5
            if 0.62 <= d <= 0.86 and dy < 0.30:
                farbe = BOGEN
            # Keine Sprechblasen-Spitze: Auf 48 Pixeln wird daraus ein Klumpen.
            # Der offene Bogen ueber der Linie traegt das Zeichen allein.

            # Die Grundlinie: der Beleg, auf dem alles steht.
            if 0.52 <= dy <= 0.70 and abs(dx) <= 0.80:
                farbe = BELEG
            # Zwei Marken auf der Linie — die Fundstellen.
            if 0.52 <= dy <= 0.70 and (abs(dx + 0.36) <= 0.075 or abs(dx - 0.36) <= 0.075):
                farbe = TEXT

            # Weiche Kante gegen Treppen: nur am Ringrand, sonst bleibt es hart.
            if 0.86 < d <= 0.90 and dy < 0.30:
                farbe = _mische(BOGEN, GRUND, (d - 0.86) / 0.04)
            if 0.58 <= d < 0.62 and dy < 0.30:
                farbe = _mische(GRUND, BOGEN, (d - 0.58) / 0.04)

            zeilen.extend(farbe)
    return bytes(zeilen)


def _png(kante: int, roh: bytes) -> bytes:
    def block(art: bytes, inhalt: bytes) -> bytes:
        k = art + inhalt
        return struct.pack(">I", len(inhalt)) + k + struct.pack(">I", zlib.crc32(k))

    kopf = struct.pack(">IIBBBBB", kante, kante, 8, 2, 0, 0, 0)  # 8 Bit, RGB
    return (b"\x89PNG\r\n\x1a\n"
            + block(b"IHDR", kopf)
            + block(b"IDAT", zlib.compress(roh, 9))
            + block(b"IEND", b""))


def main() -> None:
    for name, kante, maskierbar in (
        ("icon-192.png", 192, False),
        ("icon-512.png", 512, False),
        ("icon-maskable-512.png", 512, True),
    ):
        ziel = HIER / name
        ziel.write_bytes(_png(kante, _zeichne(kante, maskierbar)))
        print(f"  {name}: {ziel.stat().st_size} Bytes")


if __name__ == "__main__":
    main()
