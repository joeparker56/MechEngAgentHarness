"""Host-side unit tests for the CalculiX writer/parser (no ccx or gmsh needed)."""

from pathlib import Path

import numpy as np
import pytest

from mecheng.fea.calculix import (
    check_equilibrium,
    parse_dat_displacements,
    parse_dat_total_force,
    write_static_inp,
)
from mecheng.mesh.gmsh_mesh import TetMesh
from mecheng.smoke import analytic_tip_deflection

DAT = """
 displacements (vx,vy,vz) for set NALL and time  0.1000000E+01

         1  0.000000E+00  0.000000E+00  0.000000E+00
         2  1.250000E-03 -2.500000E-04 -1.919000E-01
        10  -3.5E-05  0.0  4.2e-02
"""


def _unit_tet() -> TetMesh:
    return TetMesh(
        node_ids=np.array([1, 2, 3, 4]),
        coords=np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float),
        elements=np.array([[1, 2, 3, 4]]),
        order=1,
    )


def test_parse_dat_displacements(tmp_path: Path):
    dat = tmp_path / "job.dat"
    dat.write_text(DAT)
    u = parse_dat_displacements(dat)
    assert sorted(u) == [1, 2, 10]
    np.testing.assert_allclose(u[2], [1.25e-3, -2.5e-4, -0.1919])
    np.testing.assert_allclose(u[10], [-3.5e-5, 0.0, 4.2e-2])


def test_parse_dat_uses_last_block(tmp_path: Path):
    dat = tmp_path / "job.dat"
    dat.write_text(DAT + DAT.replace("-1.919000E-01", "-9.000000E-01"))
    assert parse_dat_displacements(dat)[2][2] == pytest.approx(-0.9)


def test_write_static_inp(tmp_path: Path):
    inp = tmp_path / "job.inp"
    write_static_inp(inp, _unit_tet(), [1, 2, 3], [4], (0.0, 0.0, -10.0), 210000.0, 0.3)
    text = inp.read_text()
    assert "*ELEMENT, TYPE=C3D4, ELSET=EALL" in text
    assert "1, 1, 2, 3, 4" in text
    assert "*NSET, NSET=FIXED\n1, 2, 3\n" in text
    assert "LOADED, 3, -10" in text
    assert "LOADED, 1" not in text  # zero components are omitted
    assert "210000, 0.3" in text


TOTALS = """
 total force (fx,fy,fz) for set FIXED and time  0.1000000E+01

       -8.878409E-11  6.722658E-10  1.000000E+02
"""


def test_parse_total_force_and_equilibrium(tmp_path: Path):
    dat = tmp_path / "job.dat"
    dat.write_text(DAT + TOTALS)
    np.testing.assert_allclose(parse_dat_total_force(dat, "FIXED"), [0, 0, 100.0], atol=1e-9)
    check_equilibrium(dat, (0.0, 0.0, -100.0))
    with pytest.raises(RuntimeError, match="Equilibrium"):
        check_equilibrium(dat, (0.0, 0.0, -90.0))


def test_element_indices_are_zero_based():
    mesh = _unit_tet()
    mesh.node_ids = np.array([10, 20, 30, 40])
    mesh.elements = np.array([[40, 10, 20, 30]])
    np.testing.assert_array_equal(mesh.element_indices(), [[3, 0, 1, 2]])


def test_analytic_reference_value():
    # PL^3/3EI = 0.190476 mm, shear term adds ~0.001486 mm
    assert analytic_tip_deflection() == pytest.approx(0.19196, rel=1e-4)
