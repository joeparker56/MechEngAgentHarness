---
noteId: "e52c4a80cbaa11f1a36f9130bcfa7793"
tags: []

---

# Reference: t1/cantilever-tip-deflection

Steel cantilever, 100 × 10 × 10 mm, E = 210 GPa, ν = 0.3. Clamped at x = 0; 100 N in −z
spread uniformly over the nodes of the x = 100 face. Quantity: mean z-displacement of the
tip-face nodes. Study script: `cantilever_convergence.py`, run on 2026-10-19 with mecheng-fea:dev
(CalculiX 2.20, gmsh 4.15.2). The clamp reaction balanced the applied load (100.0 N) in every run.

| Element | Size (mm) | Elements | Nodes | Tip w (mm) |
|---|---|---|---|---|
| C3D4 | 2.5 | 3,619 | 1,082 | 0.15993 |
| C3D4 | 1.25 | 24,861 | 5,698 | 0.18116 |
| C3D10 | 5.0 | 433 | 998 | 0.19014 |
| C3D10 | 2.5 | 3,619 | 6,661 | 0.19045 |
| C3D10 | 1.67 | 11,022 | 18,295 | 0.19054 |
| C3D10 | 1.25 | 24,861 | 39,463 | 0.19058 |

**Reference value: 0.1906 mm** (converged C3D10). Grader tolerance: ±3%, i.e. [0.1849, 0.1963] mm.

## Cross-checks
- **Euler–Bernoulli beam theory** (PL³/3EI): 0.19048 mm.
- **Timoshenko beam theory** (κ = 5/6): 0.19196 mm, which is 0.7% above the 3D value.
  - The full clamp also restrains Poisson contraction and warping at the root, which slightly stiffens the 3D model.
  - A hand calculation therefore also passes. This is acceptable for a T1 task; the grader can't tell how the number was obtained.

## What the grader distinguishes
- Coarse linear tets (C3D4 at 2.5 mm: −16%; at 1.25 mm: −4.9%) **fail**. The instruction warns about this.
- A units error (E given in GPa with lengths in mm) gives roughly 1000× the deflection and **fails**. This is the `SOLUTION=wrong` oracle variant.
