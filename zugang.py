"""Zugangsdaten aus der Umgebung (oder aus ``.env``, siehe ``pfade.py``).

Jeder Zugang hat eine eigene TeachBuddy-Variable, damit Kosten trennbar
bleiben (E-11a). Für OpenAI greift ersatzweise das übliche ``OPENAI_API_KEY``.
Geheimnisse gehören nicht in Anwendungscode.
"""
import os

import pfade  # noqa: F401  — liest .env, bevor hier gefragt wird

_KETTEN = {
    "azure_endpoint":   ("TEACHBUDDY_AZURE_OPENAI_ENDPOINT",),
    "azure_key":        ("TEACHBUDDY_AZURE_OPENAI_KEY",),
    "azure_deployment": ("TEACHBUDDY_AZURE_OPENAI_DEPLOYMENT",),
    "openai_key":       ("TEACHBUDDY_OPENAI_API_KEY",          "OPENAI_API_KEY"),
}


class ZugangFehlt(RuntimeError):
    """Sagt, welche Variablen gesucht wurden — nicht nur, dass etwas fehlt."""


def hole(name: str, *, pflicht: bool = True) -> str | None:
    kette = _KETTEN[name]
    for var in kette:
        wert = os.environ.get(var)
        if wert:
            return wert
    if pflicht:
        raise ZugangFehlt(
            "%s nicht gefunden. Gesucht in dieser Reihenfolge: %s"
            % (name, " → ".join(kette))
        )
    return None


def herkunft(name: str) -> str | None:
    """Welche Variable tatsächlich gegriffen hat — für Protokolle und Kostenzuordnung."""
    for var in _KETTEN[name]:
        if os.environ.get(var):
            return var
    return None


def preis_pro_minute() -> float:
    return float(os.environ.get("TEACHBUDDY_REALTIME_PREIS_PRO_MINUTE", "0.05"))


def waehrung() -> str:
    return os.environ.get("TEACHBUDDY_WAEHRUNG", "USD")
