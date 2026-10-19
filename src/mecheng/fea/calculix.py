"""Write, run and parse CalculiX (ccx) linear-static jobs.

Units convention: mm, N, MPa (so E in MPa, results in mm and MPa).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mecheng.mesh.gmsh_mesh import TetMesh

_FLOAT = r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?"


def _write_nset(f, name: str, labels) -> None:
    f.write(f"*NSET, NSET={name}\n")
    labels = list(labels)
    for i in range(0, len(labels), 16):
        f.write(", ".join(str(n) for n in labels[i : i + 16]) + "\n")


def write_static_inp(
    path: Path,
    mesh: TetMesh,
    fixed_nodes,
    load_nodes,
    total_force: tuple[float, float, float],
    youngs_modulus: float,
    poisson_ratio: float,
) -> None:
    """Linear-static job: clamp `fixed_nodes`, spread `total_force` evenly over `load_nodes`."""
    etype = "C3D10" if mesh.order == 2 else "C3D4"
    load_nodes = list(load_nodes)
    per_node = [c / len(load_nodes) for c in total_force]

    with open(path, "w") as f:
        f.write("*HEADING\nmecheng linear static\n")
        f.write("*NODE, NSET=NALL\n")
        f.writelines(
            f"{nid}, {x:.9g}, {y:.9g}, {z:.9g}\n"
            for nid, (x, y, z) in zip(mesh.node_ids, mesh.coords)
        )
        f.write(f"*ELEMENT, TYPE={etype}, ELSET=EALL\n")
        f.writelines(
            f"{eid}, " + ", ".join(str(n) for n in conn) + "\n"
            for eid, conn in enumerate(mesh.elements, start=1)
        )
        _write_nset(f, "FIXED", fixed_nodes)
        _write_nset(f, "LOADED", load_nodes)
        f.write("*MATERIAL, NAME=MAT\n*ELASTIC\n")
        f.write(f"{youngs_modulus:.9g}, {poisson_ratio:.9g}\n")
        f.write("*SOLID SECTION, ELSET=EALL, MATERIAL=MAT\n")
        f.write("*BOUNDARY\nFIXED, 1, 3\n")
        f.write("*STEP\n*STATIC\n*CLOAD\n")
        for dof, val in enumerate(per_node, start=1):
            if val != 0.0:
                f.write(f"LOADED, {dof}, {val:.9g}\n")
        f.write("*NODE PRINT, NSET=NALL\nU\n")
        f.write("*NODE PRINT, NSET=FIXED, TOTALS=ONLY\nRF\n")
        f.write("*NODE FILE\nU\n*EL FILE\nS\n")
        f.write("*END STEP\n")


@dataclass
class CcxRun:
    returncode: int
    log_tail: str
    dat_path: Path
    frd_path: Path


def run_ccx(job_dir: Path, jobname: str, timeout_s: float = 600, threads: int = 1) -> CcxRun:
    """Run `ccx -i jobname` in job_dir. Raises if ccx isn't installed or the run fails.

    `threads` defaults to 1: we saw intermittent wrong displacements (with no error) from the
    multithreaded SPOOLES solver in the Debian ccx build. Always pair solves with
    `check_equilibrium`.
    """
    exe = shutil.which("ccx")
    if exe is None:
        raise FileNotFoundError("CalculiX executable 'ccx' not found on PATH")
    env = {"OMP_NUM_THREADS": str(threads), "CCX_NPROC_EQUATION_SOLVER": str(threads)}
    proc = subprocess.run(
        [exe, "-i", jobname],
        check=False,  # failures are detected below, with the log tail in the message
        cwd=job_dir,
        capture_output=True,
        text=True,
        timeout=timeout_s,
        env={**os.environ, **env},
    )
    tail = "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])
    run = CcxRun(proc.returncode, tail, job_dir / f"{jobname}.dat", job_dir / f"{jobname}.frd")
    if proc.returncode != 0 or "*ERROR" in proc.stdout:
        raise RuntimeError(f"ccx failed (rc={proc.returncode}):\n{tail}")
    return run


def parse_dat_displacements(dat_path: Path) -> dict[int, np.ndarray]:
    """Parse the last `displacements` block of a ccx .dat file into {node: (ux, uy, uz)}."""
    text = Path(dat_path).read_text()
    blocks = re.split(r"\n\s*displacements \(vx,vy,vz\)[^\n]*\n", text)
    if len(blocks) < 2:
        raise ValueError(f"No displacement block in {dat_path}")
    row = re.compile(rf"^\s*(\d+)\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$")
    out: dict[int, np.ndarray] = {}
    for line in blocks[-1].splitlines():
        m = row.match(line)
        if m:
            out[int(m.group(1))] = np.array([float(m.group(i)) for i in (2, 3, 4)])
        elif out and line.strip():
            break  # end of block
    return out


def parse_dat_total_force(dat_path: Path, nset: str) -> np.ndarray:
    """Parse the last `total force (fx,fy,fz) for set <nset>` block (from TOTALS=ONLY)."""
    text = Path(dat_path).read_text()
    pattern = (
        rf"total force \(fx,fy,fz\) for set {re.escape(nset)}[^\n]*\n\s*\n"
        rf"\s*({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})"
    )
    matches = re.findall(pattern, text, flags=re.IGNORECASE)
    if not matches:
        raise ValueError(f"No total force block for set {nset} in {dat_path}")
    return np.array([float(v) for v in matches[-1]])


def check_equilibrium(
    dat_path: Path, applied_force, nset: str = "FIXED", rel_tol: float = 1e-3
) -> np.ndarray:
    """Raise if the reaction at `nset` doesn't balance `applied_force`. Returns the reaction."""
    reaction = parse_dat_total_force(dat_path, nset)
    applied = np.asarray(applied_force, dtype=float)
    residual = np.linalg.norm(reaction + applied)
    if residual > rel_tol * max(np.linalg.norm(applied), 1e-12):
        raise RuntimeError(
            f"Equilibrium check failed: reaction {reaction} vs applied {applied} at {nset}"
        )
    return reaction
