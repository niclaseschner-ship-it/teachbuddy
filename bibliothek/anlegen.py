"""Eine eigene, leere Bibliothek anlegen — als eigenes Git-Repo.

    python -m bibliothek.anlegen ~/lernen/bibliothek
    python -m bibliothek.anlegen ~/lernen/bibliothek --env   # auch in .env eintragen

Die Bibliothek liegt außerhalb dieses Repos, damit eigene Inhalte und
Updates von TeachBuddy sich nicht in die Quere kommen. Sie ist ein eigenes
Git-Repo, weil die Freigabe ein Commit ist (BIB-18a): Die Pipeline schlägt
vor, `git diff` zeigt was, ein Commit gibt frei.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import pfade

ORDNER = ("pfade", "kapitel", "mindmap", "pruefung", "eingang",
          "quellen", "belege", "einheiten", "bilder/lektionen")

README = """# Meine TeachBuddy-Bibliothek

Hier liegt, was gilt und woher es stammt. Aufbau und Regeln:
https://github.com/niclaseschner-ship-it/teachbuddy/blob/main/demo/README.md

Erste Schritte stehen in `docs/eigener-lernpfad.md` im TeachBuddy-Repo:
einen Lernpfad unter `pfade/` beschreiben, ein Kapitel unter `kapitel/`
anlegen, dann `python -m pipeline.nachtlauf --nur K-01`.
"""

GITIGNORE = """# Gebaut, nicht versioniert (BIB-18b)
index.db
index.db-*
__pycache__/
"""


def anlegen(ziel: Path) -> None:
    if ziel.exists() and any(ziel.iterdir()):
        raise SystemExit(f"{ziel} ist nicht leer — dort lege ich nichts an.")
    for ordner in ORDNER:
        (ziel / ordner).mkdir(parents=True, exist_ok=True)
    for leer in ("quellen", "belege", "einheiten", "pruefung", "mindmap", "bilder/lektionen"):
        (ziel / leer / ".gitkeep").write_text("")
    (ziel / "README.md").write_text(README, encoding="utf-8")
    (ziel / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    try:
        subprocess.run(["git", "init", "-q"], cwd=ziel, check=True)
        subprocess.run(["git", "add", "-A"], cwd=ziel, check=True)
        subprocess.run(["git", "-c", "user.name=TeachBuddy", "-c",
                        "user.email=teachbuddy@localhost", "commit", "-q", "-m",
                        "Leere Bibliothek angelegt"], cwd=ziel, check=True)
    except (OSError, subprocess.CalledProcessError) as f:
        print(f"Hinweis: Git-Repo nicht angelegt ({f}). Freigabe per Commit geht dann nicht.",
              file=sys.stderr)


def in_env_eintragen(ziel: Path) -> None:
    env = pfade.REPO / ".env"
    zeilen = env.read_text(encoding="utf-8").splitlines() if env.is_file() else []
    zeilen = [z for z in zeilen if not z.startswith("TEACHBUDDY_WISSEN=")]
    zeilen.append(f"TEACHBUDDY_WISSEN={ziel}")
    env.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Eine eigene, leere Bibliothek anlegen")
    p.add_argument("ziel", help="Ordner der neuen Bibliothek")
    p.add_argument("--env", action="store_true", help="TEACHBUDDY_WISSEN in .env setzen")
    a = p.parse_args(argv)
    ziel = Path(a.ziel).expanduser().resolve()
    anlegen(ziel)
    print(f"Bibliothek angelegt: {ziel}")
    if a.env:
        in_env_eintragen(ziel)
        print("TEACHBUDDY_WISSEN steht jetzt in .env — die App zeigt ab dem nächsten Start diese Bibliothek.")
    else:
        print(f"Damit die App sie zeigt: TEACHBUDDY_WISSEN={ziel} in .env setzen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
