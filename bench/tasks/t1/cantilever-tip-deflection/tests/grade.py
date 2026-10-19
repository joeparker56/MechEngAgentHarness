"""Grader for cantilever-tip-deflection.

reward.json holds numeric metrics only (Harbor requirement); human-readable notes go to
details.json alongside it.
"""

import json
import math
from pathlib import Path

# Converged 3D C3D10 solution (mean tip w), see bench/references/cantilever-tip-deflection.md
REFERENCE_MM = 0.1906
REL_TOL = 0.03

RESULTS = Path("/app/output/results.json")
VERIFIER = Path("/logs/verifier")

metrics: dict[str, float] = {"reward": 0, "file_ok": 0, "schema_ok": 0, "within_tol": 0}
notes: list[str] = []

try:
    data = json.loads(RESULTS.read_text())
    metrics["file_ok"] = 1
except FileNotFoundError:
    notes.append(f"missing {RESULTS}")
    data = None
except json.JSONDecodeError as e:
    notes.append(f"results.json is not valid JSON: {e}")
    data = None

if data is not None:
    w = data.get("tip_deflection_mm")
    n = data.get("n_elements")
    if isinstance(w, (int, float)) and math.isfinite(w) and isinstance(n, int) and n > 0:
        metrics["schema_ok"] = 1
        rel = abs(abs(w) - REFERENCE_MM) / REFERENCE_MM
        metrics["rel_error"] = rel
        metrics["within_tol"] = int(rel <= REL_TOL)
        notes.append(f"reported {w:.6g} mm vs reference {REFERENCE_MM} mm (rel err {rel:.2%})")
    else:
        notes.append(f"bad schema: tip_deflection_mm={w!r}, n_elements={n!r}")

metrics["reward"] = int(metrics["schema_ok"] and metrics["within_tol"])

VERIFIER.mkdir(parents=True, exist_ok=True)
(VERIFIER / "reward.json").write_text(json.dumps(metrics))
(VERIFIER / "details.json").write_text(json.dumps({"notes": notes, **metrics}, indent=2))
print(json.dumps({"notes": notes, **metrics}, indent=2))
