"""Die Bibliothek: Dateien lesen, Index bauen, Index abfragen.

Die Wahrheit liegt in der Bibliothek (``TEACHBUDDY_WISSEN``) als Markdown mit YAML-Frontmatter
(BIB-18, E-9). Dieses Paket macht daraus eine wegwerfbare SQLite-Datei
(BIB-18b) und beantwortet darauf, was Dateien schlecht koennen:
Rueckwaertskanten, Volltextsuche, Belegaufloesung und BIB-20.
"""

from .lesen import Bibliothek, Befund, lies_bibliothek

__all__ = ["Bibliothek", "Befund", "lies_bibliothek"]
