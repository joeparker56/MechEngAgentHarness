"""Geometry measurement and export for build123d shapes.

Units: whatever the model was built in. The harness convention is mm.
"""

from __future__ import annotations

from pathlib import Path

from build123d import Shape, export_step, import_step


def measure(shape: Shape) -> dict:
    """Return basic geometric properties used for checks and agent feedback."""
    bb = shape.bounding_box()
    com = shape.center()
    return {
        "is_valid": bool(shape.is_valid),
        "n_solids": len(shape.solids()),
        "n_faces": len(shape.faces()),
        "n_edges": len(shape.edges()),
        "volume": shape.volume,
        "area": shape.area,
        "bbox_min": [bb.min.X, bb.min.Y, bb.min.Z],
        "bbox_max": [bb.max.X, bb.max.Y, bb.max.Z],
        "bbox_size": [bb.size.X, bb.size.Y, bb.size.Z],
        "center_of_mass": [com.X, com.Y, com.Z],
    }


def export_step_checked(shape: Shape, path: Path, rel_tol: float = 1e-6) -> dict:
    """Export to STEP, re-import, and confirm the volume survives the round trip."""
    path.parent.mkdir(parents=True, exist_ok=True)
    export_step(shape, str(path))
    reimported = import_step(str(path))
    v0, v1 = shape.volume, reimported.volume
    ok = abs(v1 - v0) <= rel_tol * max(abs(v0), 1e-12)
    return {"path": str(path), "volume": v0, "reimport_volume": v1, "round_trip_ok": ok}
