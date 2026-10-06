"""Die Proben legen ihre Dateien unter `arbeit/`, nicht ins System-Temp (APP-11).

Diese Tests schreiben echte MP3s. Auf kleinen Geräten ist `/tmp` oft ein
RAM-Dateisystem, und pytests `tmp_path` landet ohne Zutun genau dort. Deshalb
wird `TMPDIR` umgebogen, bevor pytest sein Basisverzeichnis auflöst — das
passiert erst beim ersten `tmp_path`, also nach dem Import dieser Datei.
"""

import os
import tempfile

import pfade

_ARBEIT = str(pfade.ARBEIT / "proben")
os.makedirs(_ARBEIT, exist_ok=True)
os.environ["TMPDIR"] = _ARBEIT
tempfile.tempdir = _ARBEIT
