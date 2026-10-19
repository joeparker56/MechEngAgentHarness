---
noteId: "b8dc6550cba511f1a36f9130bcfa7793"
tags: []

---

# MechEng Agent Harness: Project Plan

**Goal:** an agent harness that lets LLM agents do real mechanical-engineering work across CAD, meshing, FEA and CFD, plus **MechBench**, a benchmark of engineering tasks with automated, physics-verified grading.

Supporting research with citations is in [RESEARCH.md](RESEARCH.md).

---

## 1. Design principles (drawn from the research)

1. **Code-first, not GUI-first.** Agents write build123d, Gmsh, CalculiX-deck and OpenFOAM-dictionary code. Every published system that works well does this, and it keeps runs reproducible and easy to grade.
2. **Tight feedback loops are the main lever.**
   - Return errors and tracebacks to the agent. Foam-Agent's error-correction loop alone was worth +36 percentage points.
   - Return geometric measurements and rendered views. CADCodeVerify and CADSmith show these loops cut geometric error by an order of magnitude.
   - Return solver logs and convergence checks.
3. **Retrieval over docs and examples.** Pinned-version API docs, tutorials and worked examples close most of the gap on less-common APIs such as build123d and OpenFOAM v2606.
4. **"It ran" is not "it's correct".** FEABench found 88% of agent API calls executed but 0 problems were fully solved. Graders must check physics, not just exit codes.
5. **Tools are implemented once as the `mecheng` Python library and CLI, inside pinned Docker images.**
   - Our LangGraph agent runs on the host as a Harbor *external agent* and calls them through `environment.exec(...)`. This keeps API keys out of task containers.
   - Thin MCP servers wrap the same functions so off-the-shelf agents such as Claude Code and Codex can use them inside the container.
6. **Benchmark tasks use the standard Harbor/Terminal-Bench layout,** so the benchmark works with existing agent runners.

---

## 2. Tool stack

| Layer | Primary | Secondary / later |
|---|---|---|
| CAD | **build123d** on OCCT | CadQuery (dataset compatibility), FreeCAD headless (drawings, assemblies) |
| Geometry checks | OCP/build123d properties, trimesh (Chamfer distance, IoU) | — |
| Meshing | **Gmsh Python API** | Netgen, snappyHexMesh, cfMesh |
| FEA | **CalculiX (ccx)** | FEniCSx (custom PDEs), scikit-fem (independent cross-checks), Code_Aster |
| CFD | **OpenFOAM v2606 (ESI)** in `opencfd/openfoam-default`, driven by **foamlib** | — |
| Post-processing | meshio, ccx2paraview, **PyVista** off-screen rendering | ParaView pvbatch |
| Materials | Local YAML/JSON material database (E, ν, ρ, σy, σuts, k, cp, …) | — |
| Hand calculations | Python (sympy / pint for units) | — |

**Host:** Windows 11 with Docker Desktop on a WSL2 backend. All solvers run in Linux containers, and run-time case files live in container volumes for I/O speed. The repo stays where it is; this folder is not cloud-synced.

---

## 3. Architecture

```
┌────────────────────────── Agent (any framework / model) ──────────────────────────┐
│  Reference agent: LangGraph state graph (plan → act → verify → review → loop)     │
└───────────────────────────────┬───────────────────────────────────────────────────┘
                                │ environment.exec → mecheng CLI/library (MCP wrappers for other agents)
┌───────────────────────────────▼───────────────────────────────────────────────────┐
│ Task container (pinned image: mecheng-base + per-domain layers)                   │
│                                                                                   │
│  Tool modules:                                                                    │
│   cad-mcp     run_cad_script, measure(volume,bbox,com,faces,holes), render_views, │
│               export(step/stl), compare_to_reference                              │
│   mesh-mcp    mesh_step(gmsh params), mesh_quality, render_mesh                   │
│   fea-mcp     write/validate_inp, run_ccx, parse_results(max vm, disp, freqs),    │
│               render_field, mesh_convergence_study                                │
│   cfd-mcp     clone_tutorial, edit_dict (foamlib), run_case(blockMesh/snappy/     │
│               solver), parse_log(residuals, errors), extract_fields/forces,       │
│               render_slice                                                        │
│   kb-mcp      search_docs(build123d/gmsh/ccx/openfoam), materials_lookup,         │
│               search_examples                                                     │
│  + generic shell / python / file tools                                            │
│                                                                                   │
│  /workspace  (agent-writable)       /tests (mounted only at grading time)         │
└───────────────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────────┐
│ Runner & eval: Harbor (task format + `harbor run`), custom LangGraph agent class  │
│  trajectories (JSONL), artifacts (STEP/mesh/results), tokens, $, wall time,       │
│  solver-call counts → results DB → internal reports                               │
└───────────────────────────────────────────────────────────────────────────────────┘
```

Tool design rules:
- Return structured JSON with explicit units, for example `{"max_von_mises": {"value": 212.4, "unit": "MPa"}, "converged": true}`.
- Truncate logs to the relevant error region.
- Return images as PNG so VLMs can critique them.
- Every tool call has a timeout and resource limits. Rendering and metric calculation happen inside the tools so the agent doesn't have to write them.

---

## 4. Benchmark design (MechBench)

### 4.1 Task format (Harbor-compatible)
```
tasks/<tier>/<task-id>/
  instruction.md        # engineering brief (units, requirements, deliverables)
  task.toml             # timeouts, CPU/mem, tool stack, tags, difficulty
  environment/Dockerfile
  solution/solve.sh     # oracle reference solution, must pass the grader
  solution/wrong.sh     # deliberately flawed solution, must fail (checks the grader)
  tests/test.sh         # hidden grader → writes reward.json (score 0-1 + per-check breakdown)
  generator.py          # optional: parametric instance generator (seeded)
```

**Deliverables contract:** the agent writes `/workspace/output/` containing:
- `part.step` and/or a case directory
- `results.json`, following a schema with units
- an optional `report.md`

### 4.2 Difficulty tiers

| Tier | Description | Example tasks | Grading |
|---|---|---|---|
| **T0: Tool literacy** | Single tool call, well specified | Model a flanged bushing to given dimensions; run the lid-driven cavity at Re=100 | B-rep property tests; field compared to reference |
| **T1: Analysis** | Given geometry, set up and solve correctly | Cantilever I-beam tip deflection and max stress; plate-with-hole stress concentration factor (Kt); modal frequencies of a bracket; drag coefficient of a cylinder at Re=20/40; pipe pressure drop | Numeric tolerance against closed-form or high-fidelity reference; mesh-convergence evidence |
| **T2: Pipeline** | Geometry → mesh → solve → extract, multiple tools | Model an L-bracket, mesh it, run FEA, report the factor of safety; heat-sink fin conduction plus convection; backward-facing step reattachment length | Every stage checked: geometry tests, mesh quality, physics result within tolerance |
| **T3: Design under constraints** | Open-ended: many valid answers | Lightest bracket with σ < σy/2 and δ < 0.5 mm under load P; a duct with ΔP < X at flow Q; shaft sizing for fatigue life | **The grader re-runs its own pinned solver on the submitted STEP**, checks the constraints, and scores the objective against the reference optimum |
| **T4: Diagnosis & iteration** | A broken or sub-optimal setup is provided | A diverging OpenFOAM case; FEA with wrong boundary conditions or units that gives plausible-looking but wrong stress; a non-manifold CAD part | Fixed result is correct; root cause identified (checked against a rubric) |

### 4.3 Grading layers (applied in order, failures reported per stage)
1. **Executes / loads:** code runs, STEP re-imports as a valid solid, the case runs to completion.
2. **Property tests (CADTests-style):**
   - B-rep queries: volume, bounding box, hole count and diameter, minimum wall thickness, face and edge topology, mating interfaces
   - mesh-quality thresholds
3. **Independent physics verification:**
   - The grader's own pinned CalculiX/OpenFOAM pipeline re-analyses the agent's geometry, so the agent's reported numbers are never trusted on their own.
   - The agent's `results.json` is also compared against the grader's numbers to catch fabrication.
4. **Numeric tolerances:**
   - Set from a mesh-convergence study on the reference solution, typically ±2–5%.
   - Unit-checked through the schema.
   - Inequalities for design constraints.
5. **LLM/VLM rubric:** only for intent, report quality and manufacturability notes. Calibrated against human labels and reported **separately** from the verifiable score.

### 4.4 Avoiding contamination and gaming
- Don't reuse OpenFOAM/COMSOL tutorials or textbook problems verbatim. Write new briefs.
- **Parametric generators:** each task randomizes dimensions, loads and materials per seed. The benchmark is **private for now**. Keep a dev split (fixed seeds, used while building the harness) and a held-out test split (unseen seeds and tasks), so the harness isn't tuned to the test tasks.
- Embed canary strings in the tasks.
- Hidden `/tests` are mounted only after the agent finishes, and output files are re-computed rather than trusted.
- Before each benchmark version is frozen, review pilot trajectories for shortcuts such as hard-coded numbers or edited result files.

### 4.5 Metrics
- pass@1, averaged over 5 or more runs with 95% confidence intervals
- pass@k and pass^k (reliability)
- mean partial-credit score
- cost per task ($, tokens), wall time, number of solver calls
- **Failure-stage breakdown:** didn't run, invalid geometry, physics fail, spec fail
- Per-tier and per-domain (CAD/FEA/CFD) results tables, and a cost-vs-score Pareto plot

**Target size for v1.0:** about 100 task templates (CAD 30 / FEA 35 / CFD 25 / cross-domain 10), giving 500+ seeded instances.

---

## 5. Repository layout

```
MechEngAgentHarness/
  harness/
    mcp_servers/{cad,mesh,fea,cfd,kb}/   # one MCP server per domain
    core/                                # sandbox exec, units, schemas, rendering, logging
    agents/reference_agent/              # LangGraph graph: nodes, state, prompts, model config
    agents/ → src/mecheng_agent/         # Harbor BaseAgent wrappers (stub_agent.py, LangGraph agent)
  graders/                               # reusable checks: brep_tests, fea_verify, cfd_verify, tolerances, rubric
  bench/tasks/{t0..t4}/…                 # Harbor-format tasks
  bench/generators/                      # parametric generators
  bench/references/                      # reference solutions + convergence studies
  docker/{base,cad,fea,cfd}/Dockerfile
  kb/                                    # pinned docs, examples, material DB
  runner/                                # harbor job configs, results aggregation, reports
  docs/
  tests/                                 # unit tests for tools and graders
```

**Language:** Python 3.12, managed with `uv`. Pydantic for schemas, pint for units, pytest.

---

## 6. Phased roadmap

### Compute budget (development phase: keep it light)
- Everything runs locally on this workstation. No cloud or HPC.
- **Per-task limits:** 2–4 CPU cores, 4 GB RAM, 10 min solver wall time, 30 min total agent time.
- **FEA:** linear-static, modal, and coarse-mesh thermal tasks. Reference meshes are under about 200k DOF, and each convergence study runs once and is cached.
- **CFD:** 2D or quasi-2D cases only (cavity, channel, 2D cylinder, backward-facing step), with laminar or simple RANS models. No 3D snappyHexMesh tasks until a later phase.
- **Models:**
  - Iterate on the harness with a cheap, fast model (e.g. Haiku/Sonnet class).
  - Use the expensive frontier models only for periodic baseline runs.
  - Use the 1-epoch smoke subset during development, and run 5 epochs only for milestone evaluations.
- **Cache everything:** reference solutions, grader re-analyses keyed by a hash of the geometry, and Docker layers.


### Phase 0: Foundations (week 1–2)
- Repo scaffold, uv, pre-commit. CI is optional and should be a private repo if used; local `uv run python scripts/dev.py test` is the gate.
- Docker images:
  - `mecheng-base`: Python, build123d, gmsh, PyVista with OSMesa/EGL, meshio, trimesh
  - `+fea`: ccx, ccx2paraview
  - `+cfd`: `opencfd/openfoam-default:2606` base plus foamlib
- Smoke test: one script runs CAD → gmsh → ccx → PyVista PNG end to end in Docker on this Windows machine.
- Install Harbor, run one of its example tasks with a built-in agent, and prototype a "hello world" custom agent class so the LangGraph integration path is confirmed early.
- **Exit criterion:** `scripts/dev.py smoke` passes locally, and `harbor run` completes one dummy task using our custom-agent stub.

**Status (2026-10-19): done.**
- Images build: `mecheng-base:dev` (build123d 0.13, gmsh 4.15, PyVista/VTK 9.7 via OSMesa) and `mecheng-fea:dev` (+ CalculiX 2.20).
- Smoke test passes: CAD → STEP round trip → C3D10 mesh → ccx → equilibrium check → PNG. Tip deflection is within 0.8% of Timoshenko theory, and the full run takes about 5 s.
- First Harbor task `t1/cantilever-tip-deflection`:
  - oracle scores 1
  - the wrong-units oracle scores 0
  - the custom `StubAgent` (external `BaseAgent`) runs end to end
  - the verifier runs in a separate container and receives `/app/output` as an artifact
- Findings to carry forward:
  - Harbor's `no-network` mode isn't supported on Docker Desktop/WSL2 (no nftables kernel support), so tasks use `public` locally.
  - Harbor requires an `environment/` directory even when `docker_image` is set.
  - We saw intermittent wrong displacements from multithreaded SPOOLES (2 of ~24 solves) that later failed to reproduce in 36 more 4-thread solves. Mitigation: 1 solver thread by default, plus a mandatory reaction-force equilibrium check.

### Phase 1: CAD tools + first tasks (week 3–4)
- `cad-mcp`: sandboxed script execution, `measure`, `render_views` (iso plus 3 orthographic views with dimension overlay), STEP/STL export with round-trip check, `compare_to_reference` (Chamfer distance, IoU).
- `graders/brep_tests.py` with a property-test DSL.
- 10 T0/T2 CAD tasks with oracle and wrong solutions. Also import a slice of CADPrompt for sanity comparison against published numbers.
- Minimal LangGraph agent: a single ReAct-style node with MCP tools plus an error loop, wrapped as a Harbor custom agent. Run it with `harbor run`.
- **Exit:** the reference agent runs end to end on the 10 tasks with logged trajectories and scores.

### Phase 2: FEA (week 5–7)
- `mesh-mcp` (Gmsh with named physical groups mapped to boundary-condition sets) and `fea-mcp`:
  - `.inp` validation/linting
  - ccx run with timeouts
  - .dat/.frd parsing into structured results
  - field rendering
  - automatic mesh-convergence helper
- `graders/fea_verify.py`: an independent re-analysis pipeline, plus scikit-fem/closed-form cross-checks.
- 15 T1/T2 FEA tasks (beams, plate with hole, pressure vessel, modal, buckling, thermal, contact) with convergence-backed tolerances.
- **Exit:** every oracle passes, every wrong solution fails, and grader false-pass/false-fail rates are measured on 20 hand-reviewed runs.

### Phase 3: CFD (week 8–10)
- `cfd-mcp` built on foamlib:
  - tutorial search and cloning
  - dictionary editing with schema hints
  - blockMesh and snappyHexMesh
  - solver run with log/residual parsing and error localization
  - forces/probes extraction
  - slice renders
- `kb-mcp`: hierarchical RAG over v2606 `$FOAM_TUTORIALS` and user guides (the Foam-Agent pattern).
- 15 T0–T2 CFD tasks: cavity, Poiseuille/pipe, cylinder Cd/St, backward-facing step, heated channel, NACA0012 polar point. Graded against analytic or literature reference data.
- **Exit:** baseline agent results on FoamBench-style tasks are in the same range as published numbers; our own tasks are graded.

### Phase 4: Reference agent v2 + comparisons (week 11–12)
- Expand the LangGraph graph into planner → executor → verifier → reviewer nodes with conditional retry edges, a visual self-critique step (CADCodeVerify-style questions on renders), best-of-N with metric-based selection, and a budget/cost governor.
- Use LangGraph checkpointing to resume long runs and to replay trajectories when debugging.
- Compare against Harbor's built-in agents (e.g. Claude Code, Codex CLI) on the same tasks, and swap models through LangChain chat-model providers.
- Ablation switches: no RAG, no renders, no error loop, no reviewer. This turns the harness into a research instrument.

### Phase 5: Benchmark v1.0 (week 13–16)
- Scale to about 100 templates, including T3 design-optimization and T4 diagnosis tasks.
- Parametric generators, then the dev split and the held-out test split (both private).
- Runner covering N epochs × models × agents. Results DB, internal HTML report, failure-stage analysis, cost-score Pareto.
- Validity study: expert review of a sample of trajectories, grader calibration, and a pass on gaming risks.
- Internal docs: datasheet and task-authoring guide. A public write-up can come later if the benchmark is opened up.

### Phase 6 (stretch)
- FreeCAD headless for drawings (GD&T, TechDraw), multi-part assemblies (MUSE-style), FEniCSx multiphysics, fluid–structure interaction (FSI), Code_Aster nonlinear and fatigue.
- Use the graders as verifiable RL rewards (GRPO), keeping training graders separate from eval graders.
- Engineering-drawing input tasks (image → CAD).

---

## 7. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Docker/OpenFOAM friction on Windows (slow bind-mount I/O) | Run cases inside container volumes, and copy only deliverables back to the host. |
| Graders are wrong, giving false passes or false fails | Oracle and wrong solutions for every task; a convergence study per reference; human calibration set; report grader error rates. |
| Tolerances too tight because mesh dependence differs between agent and grader | The grader re-meshes with its own converged settings, and tolerances come from the convergence spread. |
| Contamination of the benchmark | Original briefs, parametric seeds, private split, canaries. |
| Agents game the outputs | Hidden tests, independent re-analysis, a cross-check of agent-reported numbers against grader-computed ones. |
| Compute cost (CFD runs are slow) | See the §6 compute budget: 2D or coarse cases, hard per-task limits, cached references, a cheap model for development. |
| API drift (build123d, OpenFOAM, dolfinx) | Pin versions in images; the KB is built from the pinned versions' docs. |

---

## 8. Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Agent framework for the reference harness | **Decided:** LangGraph (model-agnostic), run on the host as a Harbor external agent (`BaseAgent`), with tools invoked inside the container |
| 2 | Eval runner | **Decided:** Harbor (task format and runner). The LangGraph agent is plugged in as a custom Harbor agent. |
| 3 | Openness | **Decided:** private for now. No public leaderboard; the dev/test split is kept for internal hygiene. Only use imported datasets (e.g. CADPrompt) internally, as sanity checks. |
| 4 | Compute | **Decided:** light and local during development (see the §6 compute budget) |
| 5 | Repo location | **Decided:** stays in its current location (not cloud-synced) |

## 9. Immediate next steps
1. `git init`, scaffold the repo layout, and set up `uv` and the Python 3.12 environment.
2. Build `mecheng-base` and the `+fea` Docker images, then run the CAD → Gmsh → ccx smoke test.
3. Implement `cad-mcp` (run, measure, render, export) and the B-rep property-test grader.
4. Author the first 5 CAD tasks in Harbor format, each with oracle and wrong solutions.
