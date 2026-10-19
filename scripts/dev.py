"""Developer task runner (stands in for `make` on Windows).

    uv run python scripts/dev.py build     # build mecheng-base:dev and mecheng-fea:dev
    uv run python scripts/dev.py smoke     # end-to-end CAD -> FEA check inside mecheng-fea:dev
    uv run python scripts/dev.py test      # host unit tests
    uv run python scripts/dev.py all       # build + test + smoke
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = [("mecheng-base:dev", "docker/base/Dockerfile"), ("mecheng-fea:dev", "docker/fea/Dockerfile")]


def sh(*cmd: str) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, check=True)


def build() -> None:
    for tag, dockerfile in IMAGES:
        sh("docker", "build", "-f", dockerfile, "-t", tag, ".")


def smoke() -> None:
    out = ROOT / "out" / "smoke"
    out.mkdir(parents=True, exist_ok=True)
    # Mount the working-tree src over the installed package so edits don't need a rebuild.
    sh("docker", "run", "--rm", "--cpus", "2", "--memory", "4g",
       "-v", f"{ROOT / 'src'}:/dev-src:ro", "-e", "PYTHONPATH=/dev-src",
       "-v", f"{out}:/out", "mecheng-fea:dev", "mecheng", "smoke", "--out", "/out")
    print(f"Artifacts in {out}")


def test() -> None:
    sh(sys.executable, "-m", "pytest", "-q")


COMMANDS = {"build": build, "smoke": smoke, "test": test}


def main() -> None:
    names = sys.argv[1:] or ["all"]
    for name in names:
        steps = ["build", "test", "smoke"] if name == "all" else [name]
        for step in steps:
            COMMANDS[step]()


if __name__ == "__main__":
    main()
