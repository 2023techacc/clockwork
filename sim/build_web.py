"""Copy the simulator modules the playtest page needs into docs/py/.

Run after changing any rules so the GitHub Pages game uses them:

    python sim/build_web.py

tests/test_web.py fails if docs/py is out of date.
"""
import hashlib
import json
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "sim", "clockwork")
DST = os.path.join(ROOT, "docs", "py", "clockwork")
MODULES = ["__init__.py", "config.py", "decks.py", "enemies.py", "engine.py", "parts.py", "rng.py", "run_mode.py"]


def expected():
    """{published path: source text} for everything under docs/py."""
    files = {}
    for name in MODULES:
        with open(os.path.join(SRC, name)) as f:
            files[f"clockwork/{name}"] = f.read()
    digest = hashlib.sha256("".join(files[k] for k in sorted(files)).encode()).hexdigest()[:12]
    manifest = {"files": sorted(files), "version": digest}
    files["manifest.json"] = json.dumps(manifest, indent=2) + "\n"
    return files


def main():
    if os.path.isdir(DST):
        shutil.rmtree(DST)
    os.makedirs(DST)
    for path, text in expected().items():
        with open(os.path.join(ROOT, "docs", "py", path), "w") as f:
            f.write(text)
    print(f"wrote {len(MODULES)} modules to docs/py/")


if __name__ == "__main__":
    main()
