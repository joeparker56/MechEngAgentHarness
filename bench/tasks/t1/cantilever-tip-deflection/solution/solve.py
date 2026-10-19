"""Reference solution: C3D10 mesh at 2.5 mm, clamp x=0, uniform tip load, report mean tip w.

--wrong-units reproduces a common mistake (Young's modulus entered in GPa while lengths are
in mm), giving a deflection ~1000x too large. The grader must fail it.
"""

import argparse
import json
from pathlib import Path

import numpy as np
from build123d import Align, Box

from mecheng.cad.geometry import export_step_checked
from mecheng.fea.calculix import (
    check_equilibrium,
    parse_dat_displacements,
    run_ccx,
    write_static_inp,
)
from mecheng.mesh.gmsh_mesh import mesh_step

parser = argparse.ArgumentParser()
parser.add_argument("--wrong-units", action="store_true")
args = parser.parse_args()

work = Path("/app/work")
out = Path("/app/output")
work.mkdir(parents=True, exist_ok=True)
out.mkdir(parents=True, exist_ok=True)

beam = Box(100.0, 10.0, 10.0, align=(Align.MIN, Align.CENTER, Align.CENTER))
export_step_checked(beam, work / "beam.step")
mesh = mesh_step(work / "beam.step", size=2.5, order=2)
fixed = mesh.nodes_where(axis=0, value=0.0)
tip = mesh.nodes_where(axis=0, value=100.0)

youngs = 210.0 if args.wrong_units else 210_000.0
load = (0.0, 0.0, -100.0)
write_static_inp(work / "beam.inp", mesh, fixed, tip, load, youngs, 0.3)
run_ccx(work, "beam")
check_equilibrium(work / "beam.dat", load)
u = parse_dat_displacements(work / "beam.dat")
tip_w = float(-np.mean([u[n][2] for n in tip]))

(out / "results.json").write_text(
    json.dumps(
        {"tip_deflection_mm": tip_w, "n_elements": mesh.n_elements, "element_type": "C3D10"},
        indent=2,
    )
)
print(f"tip deflection = {tip_w:.6f} mm ({mesh.n_elements} C3D10 elements)")
