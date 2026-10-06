"""Die Fassung der Podcast-Pipeline — was steckt in dieser Folge (AUF-18a).

**Warum es das gibt.** Am 13.09.2026 wurden Sprache und Inhalt der Folgen
dreimal am selben Tag nachgebessert. Danach lagen im Regal Folgen aus drei
verschiedenen Ständen, und an einer fertigen `folge.mp3` war nicht zu
erkennen, welchen. Die Forderung: „sag mir auch, wann die Folge gemacht
wurde bzw. welche Verbesserungen sie schon drin hat."

Das ist mehr als eine Anzeige. Ohne Fassung ist jede Rückmeldung zu einer
Folge wertlos: „klingt sperrig" beantwortet man anders, wenn die Folge von
vorgestern ist.

**Wie die Zählung läuft.** Die Fassung steigt, wenn sich ändert, *wie* eine
Folge entsteht — der Auftragstext oder eine blockierende Probe. Nicht, wenn
sich das Material ändert; dafür trägt der Auftrag den Stand der Einheiten
(AUF-7).

**Kein Build-Schritt** (E-5). Die Zahl steht hier, von Hand gepflegt. Damit
sie nicht lügt, hält jeder Eintrag den Stand des Auftragstexts fest, aus dem
er entstanden ist: `pruefe_stand()` vergleicht und meldet, wenn `auftrag.md`
sich geändert hat, ohne dass jemand die Fassung erhöht hat. Eine Zahl ohne
diese Probe wäre nach zwei Tagen falsch und niemand wüsste es.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os

AUFTRAG_PFAD = os.path.join(os.path.dirname(__file__), "auftrag.md")


@dataclasses.dataclass(frozen=True)
class Fassung:
    nummer: int
    datum: str
    was: tuple[str, ...]
    regeln: tuple[str, ...]


# Neueste zuerst. Was hier steht, liest der Mensch in der App.
FASSUNGEN: tuple[Fassung, ...] = (
    Fassung(
        nummer=3,
        datum="2026-09-13",
        was=(
            "Die beiden sind Personen, nicht Funktionen: der Gast als "
            "Praktikerin, die „ich“ sagt, der Moderator als informierter "
            "Laie, der jeden Fachbegriff in eigenen Worten nachsagt.",
            "Jeder Fachbegriff wird einmal in Alltagswörtern übersetzt — "
            "daneben, nicht an seiner Stelle.",
            "Kein Nominalstil, keine „Genau“-Auftakte, Fragen tragen ein "
            "Fragezeichen (sonst liest die Sprachausgabe sie flach).",
            "Die Folge spricht nie über ihre eigene Herstellung. Vorher "
            "sagte der Moderator in 18 von 47 Folgen, dass ihm Material "
            "fehlt — jetzt blockiert eine Probe das.",
            "Ein Bild oder eine kleine Geschichte je Folge.",
        ),
        regeln=("POD-17", "POD-17a", "POD-17b", "POD-17c", "POD-17d",
                "POD-18", "POD-19"),
    ),
    Fassung(
        nummer=2,
        datum="2026-09-12",
        was=("Jede Folge rechnet ihre Theorie an einem benannten, wirklichen "
             "Fall durch — als eigener Abschnitt, nicht als Beispielsatz.",),
        regeln=("POD-16",),
    ),
    Fassung(
        nummer=1,
        datum="2026-09-11",
        was=("Erste Fassung: Gespräch aus Moderator und Gast, fünf bis zehn "
             "Minuten, jede Sprecherzeile belegt.",),
        regeln=("POD-1", "POD-3", "POD-5", "AUF-8a"),
    ),
)

JETZIGE = FASSUNGEN[0]

# Der Stand von `auftrag.md`, als Fassung 3 festgelegt wurde. Ändert sich die
# Datei, ohne dass die Fassung steigt, meldet `pruefe_stand()` das.
STAND_BEI_FESTLEGUNG = "fa16f5571bba5f54"


def stand_des_auftrags(pfad: str | None = None) -> str:
    """Kurzer Hash des Auftragstexts — dieselbe Idee wie `/version.json`."""
    with open(pfad or AUFTRAG_PFAD, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def pruefe_stand(pfad: str | None = None) -> str | None:
    """Sagt, ob die Fassung noch zum Auftragstext passt. `None` heißt: ja."""
    ist = stand_des_auftrags(pfad)
    if ist == STAND_BEI_FESTLEGUNG:
        return None
    return (
        "auftrag.md hat den Stand %s, Fassung %d wurde bei %s festgelegt. "
        "Entweder ist die Änderung klein genug (dann STAND_BEI_FESTLEGUNG in "
        "podcast/fassung.py nachziehen) oder sie gehört in eine neue Fassung."
        % (ist, JETZIGE.nummer, STAND_BEI_FESTLEGUNG)
    )


def als_fracht(nummer: int | None = None) -> dict:
    """Was in `folge.json` und in den Lektionsvertrag geht."""
    f = next((x for x in FASSUNGEN if x.nummer == nummer), JETZIGE)
    return {
        "nummer": f.nummer,
        "datum": f.datum,
        "was": list(f.was),
        "regeln": list(f.regeln),
        "auftrag_stand": stand_des_auftrags(),
    }
