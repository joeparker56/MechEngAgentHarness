"""Mesh-convergence study for t1/cantilever-tip-deflection (run inside mecheng-fea).

    docker run --rm -v <repo>:/repo -e PYTHONPATH=/repo/src mecheng-fea:dev \
        python /repo/bench/references/cantilever_convergence.py
"""

import json
import tempfile
from pathlib import Path

import numpy as np
from build123d import Align, Box

from mecheng.cad.geometry import export_step_checked
from mecheng.fea.calculix import (
    parse_dat_displacements,
    parse_dat_total_force,
    run_ccx,
    write_static_inp,
)
from mecheng.mesh.gmsh_mesh import mesh_step
from mecheng.smoke import analytic_tip_deflection

rows = []
with tempfile.TemporaryDirectory() as tmp:
    work = Path(tmp)
    beam = Box(100.0, 10.0, 10.0, align=(Align.MIN, Align.CENTER, Align.CENTER))
    export_step_checked(beam, work / "beam.step")
    for order, size in [(1, 2.5), (1, 1.25), (2, 5.0), (2, 2.5), (2, 1.67), (2, 1.25)]:
        mesh = mesh_step(work / "beam.step", size=size, order=order)
        fixed = mesh.nodes_where(0, 0.0)
        tip = mesh.nodes_where(0, 100.0)
        write_static_inp(work / "beam.inp", mesh, fixed, tip, (0, 0, -100.0), 210_000.0, 0.3)
        run_ccx(work, "beam", threads=4)
        u = parse_dat_displacements(work / "beam.dat")
        w = float(-np.mean([u[n][2] for n in tip]))
        rf = parse_dat_total_force(work / "beam.dat", "FIXED")
        rows.append({"element": "C3D10" if order == 2 else "C3D4", "size_mm": size,
                     "n_elements": mesh.n_elements, "n_nodes": mesh.n_nodes, "tip_w_mm": w,
                     "reaction_z_N": float(rf[2]), "n_parsed": len(u)})
        print(rows[-1], flush=True)

print(json.dumps({"timoshenko_mm": analytic_tip_deflection(), "rows": rows}, indent=2))
