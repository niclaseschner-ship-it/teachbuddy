# Mitarbeiten

Schön, dass du hier bist. TeachBuddy ist klein und soll es bleiben. Vier Regeln
halten es so — für Menschen und für Coding-Agenten gleichermaßen.

## Die vier Regeln

1. **`specs/` ist die Wahrheit.** Verhalten ändern heißt, die Spec im selben
   Schritt zu ändern. Code, der der Spec widerspricht, ist der Fehler.

2. **Nichts erfinden, wo etwas offen ist.** Eine Spec-Stelle mit
   `> **OFFEN (E-n):**` ist eine echte Lücke. Sie wird geschlossen, indem die
   Entscheidung in `decisions/` fällt, nicht indem jemand beim Implementieren
   eine plausible Antwort wählt. Dasselbe gilt für Inhalte: Was das Material
   nicht trägt, wird als Lücke gemeldet, nicht gefüllt.

3. **Keine LLM-API in der Erzeugung.** Recherche, Modellierung und Prüfung
   laufen über die Abo-CLIs (`claude -p`, `codex exec`, TB-5). Bezahlte
   Schnittstellen gibt es nur dort, wo der Lernende etwas erlebt:
   Sprachausgabe und Gespräch.

4. **Nichts auf Vorrat** (TB-9). Kein Modul, keine Konfiguration, keine
   Spec-Datei ohne heutigen Nutzer.

## Praktisches

- Sprache von Code, Oberfläche und Doku ist **Deutsch**. Bezeichner bleiben
  deutsch, auch neue.
- Kommentare erklären das **Warum**, nicht das Was — gern mit der Spec-ID
  (`POD-4`, `E-19`), an der die Entscheidung hängt.
- Die App hat **keinen Build-Schritt** (E-5): ES-Module, kein `node_modules`.
- Zwischendateien gehören unter `arbeit/`, nicht ins System-Temp (APP-11).
- Vor einem Pull Request: `python -m pytest` und `node --test app/tests/`.
