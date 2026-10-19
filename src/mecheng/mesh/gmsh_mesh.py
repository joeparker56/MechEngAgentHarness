"""Tetrahedral meshing of STEP geometry with the gmsh Python API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

# gmsh element type ids
_TET4 = 4
_TET10 = 11

# gmsh's 10-node tet orders the last two edge nodes (2-3, 1-3); Abaqus/CalculiX C3D10 and
# VTK quadratic tetra use (1-3, 2-3). Same permutation for both targets.
_GMSH_TO_ABAQUS_TET10 = [0, 1, 2, 3, 4, 5, 6, 7, 9, 8]


@dataclass
class TetMesh:
    """Solid tet mesh. `node_ids` are 1-based labels; `elements` holds labels, not indices."""

    node_ids: np.ndarray  # (N,)
    coords: np.ndarray  # (N, 3)
    elements: np.ndarray  # (M, 4) or (M, 10), Abaqus node order
    order: int

    @property
    def n_nodes(self) -> int:
        return len(self.node_ids)

    @property
    def n_elements(self) -> int:
        return len(self.elements)

    def nodes_where(self, axis: int, value: float, tol: float = 1e-6) -> np.ndarray:
        """Node labels lying on the plane coords[:, axis] == value."""
        mask = np.abs(self.coords[:, axis] - value) <= tol
        return self.node_ids[mask]

    def element_indices(self) -> np.ndarray:
        """Connectivity as 0-based row indices into `coords`."""
        lookup = np.full(self.node_ids.max() + 1, -1, dtype=np.int64)
        lookup[self.node_ids] = np.arange(self.n_nodes)
        return lookup[self.elements]


def mesh_step(step_path: Path, size: float, order: int = 2) -> TetMesh:
    """Mesh the solid(s) in a STEP file with tets of characteristic length `size`."""
    import gmsh

    gmsh.initialize(interruptible=False)
    try:
        gmsh.option.setNumber("General.Terminal", 0)
        gmsh.model.add("part")
        gmsh.model.occ.importShapes(str(step_path))
        gmsh.model.occ.synchronize()
        gmsh.option.setNumber("Mesh.MeshSizeMin", size)
        gmsh.option.setNumber("Mesh.MeshSizeMax", size)
        gmsh.option.setNumber("Mesh.ElementOrder", order)
        gmsh.model.mesh.generate(3)

        tags, flat_coords, _ = gmsh.model.mesh.getNodes()
        etype = _TET10 if order == 2 else _TET4
        _, conn = gmsh.model.mesh.getElementsByType(etype)
    finally:
        gmsh.finalize()

    npe = 10 if order == 2 else 4
    elements = np.asarray(conn, dtype=np.int64).reshape(-1, npe)
    if order == 2:
        elements = elements[:, _GMSH_TO_ABAQUS_TET10]

    # Keep only nodes referenced by volume elements (drops any orphan geometry nodes).
    node_ids = np.asarray(tags, dtype=np.int64)
    coords = np.asarray(flat_coords, dtype=float).reshape(-1, 3)
    used = np.isin(node_ids, np.unique(elements))
    order_idx = np.argsort(node_ids[used])
    return TetMesh(
        node_ids=node_ids[used][order_idx],
        coords=coords[used][order_idx],
        elements=elements,
        order=order,
    )
