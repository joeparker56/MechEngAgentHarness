---
noteId: "b82fe6c0cba711f1a36f9130bcfa7793"
tags: []

---

# Cantilever tip deflection (3D FEA)

A straight steel cantilever beam has a solid rectangular cross-section.

| Quantity | Value |
|---|---|
| Length (along +x) | 100 mm |
| Width (y) | 10 mm |
| Height (z) | 10 mm |
| Young's modulus | 210 GPa |
| Poisson's ratio | 0.3 |

The end face at x = 0 is fully clamped. A total force of 100 N acts in the **−z** direction,
distributed uniformly over the free end face at x = 100 mm.

Using a 3D solid finite-element analysis, determine the vertical deflection at the free end
(the mean z-displacement magnitude over the end face).

## Tools available in this environment

- Python 3.12 with `build123d`, `gmsh`, `meshio`, `pyvista`, `numpy`
- CalculiX (`ccx`) on the PATH
- The `mecheng` Python package (`mecheng.cad`, `mecheng.mesh`, `mecheng.fea`, `mecheng.render`)

## Deliverable

Write `/app/output/results.json`:

```json
{
  "tip_deflection_mm": <float, positive magnitude in mm>,
  "n_elements": <int, number of solid elements in your final mesh>,
  "element_type": "<e.g. C3D10>"
}
```

Your answer must be within 3% of a converged reference solution. Coarse linear tetrahedra
(C3D4) are known to be too stiff for this problem, so check that your mesh has converged.
