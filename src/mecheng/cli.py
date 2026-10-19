"""`mecheng` command-line entry point (runs inside task containers)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _cmd_smoke(args: argparse.Namespace) -> int:
    from mecheng import smoke

    result = smoke.run(Path(args.out))
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


def _cmd_info(args: argparse.Namespace) -> int:
    import shutil
    from importlib.metadata import PackageNotFoundError, version

    info = {"python": sys.version.split()[0], "ccx": shutil.which("ccx")}
    for pkg in ("mecheng", "build123d", "gmsh", "pyvista", "vtk", "meshio", "trimesh", "numpy"):
        try:
            info[pkg] = version(pkg)
        except PackageNotFoundError:
            info[pkg] = None
    print(json.dumps(info, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mecheng")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("smoke", help="CAD -> mesh -> CalculiX -> render end-to-end check")
    p.add_argument("--out", default="/tmp/mecheng-smoke")
    p.set_defaults(func=_cmd_smoke)

    p = sub.add_parser("info", help="Print tool versions")
    p.set_defaults(func=_cmd_info)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
