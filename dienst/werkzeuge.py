"""Die vier Werkzeuge des Gesprächspartners (DIS-24 bis DIS-29).

**Warum es sie gibt.** Rückmeldung vom 14.09.2026: „Feedback zum Gesprächspartner — er
kann nur mit Material arbeiten, das er hat, und kann keine Recherche zu
weiterführenden Fragen. Das hatten wir aber so vereinbart."

Er hat recht. DIS-25 nennt seit dem 11.09. vier Werkzeuge, OBF-17 erklärt
freies Weiterrecherchieren ausdrücklich für zulässig, solange es gekennzeichnet
ist, und OBF-18 macht daraus einen Rückkanal. Gebaut war davon **nichts**: Der
Sitzungsprompt trug das Kapitelwissen und sonst nichts, und die Anweisung
sagte dem Partner, alles Übrige wisse er nicht. `_gespraechs_anweisung` gibt
das selbst zu — „Die richtige Lösung ist die Bibliothek als Werkzeug (DIS-24,
DIS-25); bis dahin ist das hier die ehrliche Näherung."

**Warum das mehr ist als Bequemlichkeit.** Der Sitzungsprompt fasst ein großes
Kapitel nicht (16 384 Token erlaubt, K-01 braucht 90 468), also wird gestuft
gekürzt: Bei K-01 kennt der Partner von jeder Einheit nur noch den Kernsatz.
`bibliothek_nachschlagen` holt die Tiefe zurück, die dort verlorengeht — und
zwar **belegt**. Ohne das Werkzeug ist die Kürzung ein Wissensverlust, mit ihm
nur eine andere Ladereihenfolge.

**Die Trennlinie, an der alles hängt (DIS-28, TB-1).** Was aus der Bibliothek
kommt, trägt seinen Beleg. Was aus dem Netz kommt, ist ungeprüft und wird im
Gespräch als solches benannt. Beides kommt aus demselben Mund — nur die
Kennzeichnung hält es auseinander. Deshalb geben die Werkzeuge ihre Herkunft
strukturiert zurück und nicht als Fließtext, in dem sie sich verwischt.

**Warum die Recherche über die bezahlte Schnittstelle laufen darf.** TB-5 zieht
die Linie nicht zwischen Anbietern, sondern zwischen Bauen und Erleben: „Was
der Lernende erlebt, läuft über bezahlte Schnittstellen." Eine Rückfrage
mitten im Gespräch ist Erleben — niemand wartet dabei Minuten auf einen
Abo-CLI-Lauf. Der Rechercheur-Auftrag (AUF) bleibt davon unberührt; er baut
Bibliothek, das hier beantwortet eine Frage.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

__all__ = ["ERKLAERUNGEN", "nachschlagen", "recherchieren"]

# Wie viele Treffer der Partner je Nachschlagen bekommt. Mehr macht die
# Antwort nicht besser, sondern länger — und er muss sie vorlesen können.
TREFFER = 5

# DIS-27: Der Partner kennt das Tempo seiner Werkzeuge und richtet seine
# Sprache danach. Das steht deshalb in der Beschreibung, die er liest, und
# nicht nur in der Spec.
ERKLAERUNGEN: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "bibliothek_nachschlagen",
        "description": (
            "Durchsucht die GANZE Bibliothek, nicht nur das laufende Kapitel. "
            "Kommt in Millisekunden zurück — kündige es nicht an, schlag "
            "einfach nach. Nimm es, wenn du etwas genauer wissen willst, als "
            "in deiner Anweisung steht, oder wenn die Frage ein anderes "
            "Kapitel betrifft. Was hier zurückkommt, ist BELEGT: Du darfst es "
            "als gesichert behandeln und die Fundstelle nennen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "frage": {
                    "type": "string",
                    "description": "Suchbegriffe oder die Frage selbst, deutsch.",
                },
            },
            "required": ["frage"],
        },
    },
    {
        "type": "function",
        "name": "recherchieren",
        "description": (
            "Sieht im Netz nach, wenn die Bibliothek nichts hergibt. Dauert "
            "wenige Sekunden — ein kurzes „Moment, ich sehe nach“ genügt. "
            "WICHTIG: Was hier zurückkommt, ist "
            "UNGEPRÜFT und kein Beleg. Sag im Gespräch ausdrücklich, dass du "
            "das frisch nachgesehen hast und es nicht aus der Bibliothek "
            "stammt. Schlag erst in der Bibliothek nach, bevor du hierher "
            "greifst."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "frage": {
                    "type": "string",
                    "description": "Die Frage, ausformuliert.",
                },
            },
            "required": ["frage"],
        },
    },
    {
        "type": "function",
        "name": "rechercheauftrag_aufnehmen",
        "description": (
            "Hält eine Lücke für später fest, wenn weder Bibliothek noch "
            "Recherche tragen oder das Thema einen eigenen Lauf verdient. "
            "Kommt sofort zurück und ist stumm: Sag kein Wort darüber, das "
            "ist Buchhaltung, kein Gesprächsgegenstand."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "frage": {"type": "string"},
                "zusammenhang": {
                    "type": "string",
                    "description": "Worüber geredet wurde, als die Lücke auffiel.",
                },
            },
            "required": ["frage"],
        },
    },
    {
        "type": "function",
        "name": "punkt_geprueft",
        "description": (
            "Hakt einen Punkt der Agenda ab, wenn der Lernende ihn "
            "beantwortet hat. Sofort und stumm — kein „ich notiere das kurz“."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "Die Agenda-ID, etwa AG-WE-0187."},
                "urteil": {"type": "string", "enum": ["sitzt", "halb", "offen"]},
                "begruendung": {"type": "string"},
            },
            "required": ["id", "urteil"],
        },
    },
]


def nachschlagen(db, frage: str, *, treffer: int = TREFFER) -> dict[str, Any]:
    """DIS-26 — die ganze Bibliothek über den Volltextindex (BIB-18b).

    Gesucht wird über die Wissenseinheiten, nicht über die Belege: Die Einheit
    ist der Gedanke, der Beleg nur seine Fundstelle. Wer über Belege sucht,
    bekommt Zitatschnipsel ohne den Zusammenhang, in dem sie etwas heißen.

    `fts5` wirft bei roher Nutzereingabe schnell einen Syntaxfehler — ein
    Apostroph, ein Bindestrich, ein `OR` genügen. Deshalb werden die Wörter
    einzeln in Anführungszeichen gesetzt und mit OR verbunden: keine
    Fehlersyntax mehr möglich, und ein Treffer auf einem Wort ist besser als
    ein Abbruch.
    """
    worte = [w for w in "".join(
        c if c.isalnum() or c.isspace() else " " for c in (frage or "")
    ).split() if len(w) > 2]
    if not worte:
        return {"treffer": [], "hinweis": "Zu wenig Suchbegriff."}

    muster = " OR ".join('"%s"' % w for w in worte[:12])
    zeilen = db.execute(
        "SELECT f.einheit_id AS id, e.titel, e.stichwort, e.kurzfassung,"
        "       k.kapitel AS kapitel"
        "  FROM fts_einheiten f"
        "  JOIN einheiten e ON e.id = f.einheit_id"
        "  LEFT JOIN ("
        "      SELECT le.einheit_id, l.kapitel FROM lektion_einheiten le"
        "      JOIN lektionen l ON l.id = le.lektion_id GROUP BY le.einheit_id"
        "  ) k ON k.einheit_id = f.einheit_id"
        " WHERE fts_einheiten MATCH ?"
        " ORDER BY bm25(fts_einheiten) LIMIT ?",
        (muster, treffer),
    ).fetchall()

    raus = []
    for z in zeilen:
        belege = [
            r["von"] for r in db.execute(
                "SELECT von FROM kanten WHERE nach = ? AND typ = 'stuetzt'",
                (z["id"],))
        ]
        raus.append({
            "einheit": z["id"],
            "stichwort": z["stichwort"],
            "kernaussage": z["titel"],
            "kurzfassung": z["kurzfassung"],
            "kapitel": z["kapitel"],
            "belege": belege,
        })
    return {
        "treffer": raus,
        "herkunft": "bibliothek",
        "hinweis": ("Belegt. Du darfst es als gesichert behandeln."
                    if raus else
                    "Die Bibliothek gibt dazu nichts her. Wenn es wichtig ist, "
                    "recherchiere oder nimm einen Rechercheauftrag auf."),
    }


# --------------------------------------------------------------------------
# Recherche im Netz (DIS-28) — ungeprüft, und das bleibt sichtbar.
# --------------------------------------------------------------------------

# **Kein Denkmodell.** Die erste Fassung nahm `gpt-5-mini` und brauchte im
# Median 16 Sekunden, im schlechtesten Fall 30. Rückmeldung vom 14.09.2026: „33 Sekunden
# ist lange, wenn ich mit ChatGPT spreche geht das in wenigen Sekunden. Dann
# haben wir das falsche Recherche-Tool."
#
# Er hat recht, und die Ursache ist die Modellwahl: Ein Reasoning-Modell denkt
# vor und nach der Suche. Für eine Rückfrage im Gespräch ist das genau falsch —
# gefragt ist nicht die beste Antwort, sondern eine brauchbare, bevor der
# Gesprächsfaden reißt. Gemessen über dieselben drei Fragen:
#
#     gpt-4o-mini + web_search_preview   1,9 / 2,8 / 4,2 s   Median 2,8
#     gpt-5-mini  + web_search           8,3 / 16,0 / 30,0   Median 16,0
#
# `reasoning.effort: minimal` wäre der naheliegende Ausweg und geht nicht: Der
# Anbieter lehnt die Kombination mit `web_search` ausdrücklich ab (HTTP 400).
#
# `search_context_size: low` holt weniger Seitentext. Für drei Sätze reicht es,
# und es ist der zweite Hebel an der Wartezeit.
RECHERCHE_MODELL = os.environ.get("TEACHBUDDY_RECHERCHE_MODELL", "gpt-4o-mini")
RECHERCHE_WERKZEUG = {
    "type": "web_search_preview",
    "search_context_size": os.environ.get("TEACHBUDDY_RECHERCHE_TIEFE", "low"),
}
# Kurz halten: Wer im Gespräch 45 Sekunden wartet, hat das Gespräch verloren.
# Lieber eine Absage, die der Partner aussprechen kann (TB-8).
RECHERCHE_ZEIT = int(os.environ.get("TEACHBUDDY_RECHERCHE_ZEIT", "20"))


def recherchieren(frage: str, schluessel: str) -> dict[str, Any]:
    """Eine Websuche über die Responses-Schnittstelle.

    **Kurz halten ist hier eine inhaltliche Anforderung, keine Sparsamkeit.**
    Der Partner muss das Ergebnis im Gespräch aussprechen. Drei Sätze kann er
    unterbringen, einen Aufsatz nicht — der würde vorgelesen, und dann ist das
    Gespräch ein Vortrag (POD-1 gilt sinngemäß auch hier).

    Fehler werden **zurückgegeben, nicht geworfen**: Ein Werkzeug, das im
    Gespräch stumm bleibt, lässt den Partner raten. Er soll sagen können, dass
    die Suche nicht ging (TB-8).
    """
    rumpf = json.dumps({
        "model": RECHERCHE_MODELL,
        "tools": [RECHERCHE_WERKZEUG],
        "input": (
            "Beantworte knapp und auf Deutsch, in höchstens drei Sätzen: "
            + (frage or "").strip()
            + "\n\nNenne am Ende in einer Zeile die Quelle (Name und Jahr). "
            "Wenn du es nicht sicher findest, sag das, statt zu raten."
        ),
    }).encode("utf-8")
    anfrage = urllib.request.Request(
        "https://api.openai.com/v1/responses", data=rumpf,
        headers={"Authorization": f"Bearer {schluessel}",
                 "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(anfrage, timeout=RECHERCHE_ZEIT) as antwort:
            daten = json.loads(antwort.read())
    except urllib.error.HTTPError as fehler:
        return {"fehler": "anbieter_lehnt_ab",
                "hinweis": "Die Suche ging nicht (%s). Sag das im Gespraech."
                           % fehler.code}
    except Exception as fehler:                      # Netz weg, Zeit um
        return {"fehler": "nicht_erreichbar",
                "hinweis": "Die Suche ging nicht (%s). Sag das im Gespraech."
                           % type(fehler).__name__}

    return {
        "antwort": _text_aus(daten),
        "herkunft": "netz",
        "hinweis": ("UNGEPRÜFT, nicht aus der Bibliothek. Sag das ausdrücklich, "
                    "bevor du es weitergibst (DIS-28)."),
    }


def _text_aus(daten: dict[str, Any]) -> str:
    """Den Text aus einer Responses-Antwort holen.

    `output_text` ist der bequeme Weg und fehlt, sobald Werkzeuge im Spiel
    sind. Dann steht der Text in den `message`-Einträgen von `output`.
    """
    if isinstance(daten.get("output_text"), str) and daten["output_text"].strip():
        return daten["output_text"].strip()
    stuecke = []
    for eintrag in daten.get("output") or []:
        if eintrag.get("type") != "message":
            continue
        for teil in eintrag.get("content") or []:
            if isinstance(teil.get("text"), str):
                stuecke.append(teil["text"])
    return "\n".join(stuecke).strip() or "(keine Antwort)"
