"""End-to-end smoke test: build123d -> STEP -> gmsh -> CalculiX -> parse -> PyVista PNG.

Problem: steel cantilever, square section, clamped at x=0, transverse tip load at x=L.
The FEA tip deflection is checked against Timoshenko beam theory.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np

# Problem definition (mm, N, MPa)
LENGTH = 100.0
WIDTH = 10.0  # y
HEIGHT = 10.0  # z, load direction
YOUNGS = 210_000.0
POISSON = 0.3
LOAD = 100.0  # N in -z
MESH_SIZE = 2.5
TOLERANCE = 0.03


def analytic_tip_deflection() -> float:
    """Timoshenko cantilever: bending + shear deflection (shear coefficient 5/6)."""
    inertia = WIDTH * HEIGHT**3 / 12.0
    shear_modulus = YOUNGS / (2.0 * (1.0 + POISSON))
    area = WIDTH * HEIGHT
    bending = LOAD * LENGTH**3 / (3.0 * YOUNGS * inertia)
    shear = LOAD * LENGTH / ((5.0 / 6.0) * shear_modulus * area)
    return bending + shear


def run(out_dir: Path) -> dict:
    from build123d import Align, Box

    from mecheng.cad.geometry import export_step_checked, measure
    from mecheng.fea.calculix import (
        check_equilibrium,
        parse_dat_displacements,
        run_ccx,
        write_static_inp,
    )
    from mecheng.mesh.gmsh_mesh import mesh_step
    from mecheng.render import render_displacement

    out_dir.mkdir(parents=True, exist_ok=True)
    timings: dict[str, float] = {}
    t0 = time.perf_counter()

    beam = Box(LENGTH, WIDTH, HEIGHT, align=(Align.MIN, Align.CENTER, Align.CENTER))
    geometry = measure(beam)
    step = export_step_checked(beam, out_dir / "beam.step")
    timings["cad_s"] = time.perf_counter() - t0

    t = time.perf_counter()
    mesh = mesh_step(out_dir / "beam.step", size=MESH_SIZE, order=2)
    fixed = mesh.nodes_where(axis=0, value=0.0)
    tip = mesh.nodes_where(axis=0, value=LENGTH)
    timings["mesh_s"] = time.perf_counter() - t

    t = time.perf_counter()
    load = (0.0, 0.0, -LOAD)
    write_static_inp(out_dir / "beam.inp", mesh, fixed, tip, load, YOUNGS, POISSON)
    run_ccx(out_dir, "beam")
    reaction = check_equilibrium(out_dir / "beam.dat", load)
    disp = parse_dat_displacements(out_dir / "beam.dat")
    timings["solve_s"] = time.perf_counter() - t

    u = np.array([disp[n] for n in mesh.node_ids])
    tip_mask = np.isin(mesh.node_ids, tip)
    fea_tip = float(-u[tip_mask, 2].mean())
    reference = analytic_tip_deflection()  # within ~0.7% of the converged 3D answer
    rel_err = abs(fea_tip - reference) / reference

    t = time.perf_counter()
    image = render_displacement(mesh, u, out_dir / "displacement.png")
    timings["render_s"] = time.perf_counter() - t
    timings["total_s"] = time.perf_counter() - t0

    result = {
        "passed": bool(step["round_trip_ok"] and rel_err <= TOLERANCE),
        "tip_deflection_fea_mm": fea_tip,
        "tip_deflection_reference_mm": reference,
        "relative_error": rel_err,
        "reaction_force_N": reaction.tolist(),
        "tolerance": TOLERANCE,
        "geometry": geometry,
        "step": step,
        "mesh": {"n_nodes": mesh.n_nodes, "n_elements": mesh.n_elements, "size_mm": MESH_SIZE,
                 "n_fixed_nodes": len(fixed), "n_loaded_nodes": len(tip)},
        "image": image,
        "timings": timings,
    }
    (out_dir / "smoke_result.json").write_text(json.dumps(result, indent=2))
    return result
