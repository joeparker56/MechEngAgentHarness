"""Off-screen rendering of meshes and result fields to PNG (for agent visual feedback)."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from mecheng.mesh.gmsh_mesh import TetMesh


def _grid(mesh: TetMesh):
    import pyvista as pv

    celltype = pv.CellType.QUADRATIC_TETRA if mesh.order == 2 else pv.CellType.TETRA
    return pv.UnstructuredGrid({celltype: mesh.element_indices()}, mesh.coords)


def render_displacement(
    mesh: TetMesh,
    displacement: np.ndarray,
    png_path: Path,
    scale: float | None = None,
) -> dict:
    """Render the undeformed outline plus the deformed shape coloured by |U|.

    `displacement` is (N, 3), row-aligned with `mesh.node_ids`. If `scale` is None the
    deformation is exaggerated so the peak displacement is 10% of the largest part dimension.
    """
    import pyvista as pv

    grid = _grid(mesh)
    mag = np.linalg.norm(displacement, axis=1)
    grid.point_data["U"] = displacement
    grid.point_data["|U|"] = mag
    if scale is None:
        extent = float(np.ptp(mesh.coords, axis=0).max())
        scale = 0.1 * extent / mag.max() if mag.max() > 0 else 1.0
    warped = grid.warp_by_vector("U", factor=scale)

    plotter = pv.Plotter(off_screen=True, window_size=(1200, 800))
    plotter.add_mesh(grid.extract_feature_edges(), color="gray", line_width=1)
    plotter.add_mesh(warped, scalars="|U|", cmap="viridis", scalar_bar_args={"title": "|U| (mm)"})
    plotter.add_text(f"Displacement magnitude, deformation x{scale:.3g}", font_size=10)
    plotter.view_isometric()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    plotter.screenshot(str(png_path))
    plotter.close()
    return {"path": str(png_path), "deformation_scale": scale}
