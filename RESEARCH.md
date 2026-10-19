# Research Notes: LLM Agents for Engineering Software (as of Oct 2026)

Condensed from web research run on 2026-10-19. Items marked *(verify)* came only from secondary sources.

---

## 1. Agents + CAD

### Substrate: code-as-CAD wins
LLMs write Python against an OpenCascade (OCCT) kernel library. The harness runs it in a sandbox and feeds back tracebacks, geometric measurements and rendered views. This approach beats driving a GUI through MCP on reproducibility, diffing and grading.

| Tool | Notes |
|---|---|
| **build123d** | Pythonic OCCT API with native STEP/STL export. In CADDesigner's comparison it scored pass@1 0.59 vs CadQuery's 0.50, and execution success 96% vs 87.5%. **Recommended default.** |
| **CadQuery** | Most datasets and fine-tuned models target it (CAD-Recode, cadrille, CAD-Coder, CADEvolve). Use it for fine-tuning, or for compatibility with existing benchmarks. |
| **FreeCAD Python** | Verbose, and LLMs make more errors with it. Useful for TechDraw drawings, the FEM workbench and assemblies. |
| **OpenSCAD** | CSG/mesh only, no STEP output. Poor fit for mechanical work. |
| **Onshape / Fusion MCP** | Official MCP servers exist. They are cloud/GUI-bound and not reproducible enough for a benchmark. |

### Key papers and systems
- **CADCodeVerify + CADPrompt** ([2410.05340](https://arxiv.org/abs/2410.05340)): a VLM asks itself verification questions about renders, then corrects the code. Comes with a 200-prompt benchmark.
- **CAD-Assistant** ([2412.13810](https://arxiv.org/abs/2412.13810), ICCV'25): VLLM planner with FreeCAD tools (render, cross-section, sketch parameterizer).
- **CADDesigner** ([2508.01031](https://arxiv.org/abs/2508.01031)): visual feedback plus a retrieval knowledge base.
- **CAD-Recode** ([2412.14042](https://arxiv.org/abs/2412.14042)): best-of-N sampling, selecting by Chamfer distance.
- **cadrille** ([2505.22914](https://arxiv.org/abs/2505.22914), ICLR'26): SFT, then GRPO with geometric rewards.
- **CAD-Coder** ([2505.19713](https://arxiv.org/abs/2505.19713)): GRPO with a Chamfer-distance reward.
- **CADEvolve** ([2602.16317](https://arxiv.org/abs/2602.16317)): evolves CadQuery generators into 1.3M scripts.
- **agentcad** (MCP + CLI for build123d/CadQuery with checks and multi-view renders) and **Primus** (a reviewer subagent that checks API usage). Both are reference designs for our CAD tool layer.

---

## 2. Agents + CFD (OpenFOAM)

| System | Architecture | Result |
|---|---|---|
| **Foam-Agent 2.0** ([2509.18178](https://arxiv.org/abs/2509.18178), [code](https://github.com/csml-rpi/Foam-Agent)) | Architect → writer → runner → reviewer. Hierarchical RAG over tutorials, Gmsh/snappyHexMesh meshing, tools exposed via MCP. | 88.2% on FoamBench Basic, 62.5% on Advanced |
| **MetaOpenFOAM 2.0** ([2502.00498](https://arxiv.org/abs/2502.00498)) | MetaGPT-style pipeline with CoT decomposition | 86.9% on its own cases |
| **ChatCFD** ([2506.02019](https://arxiv.org/abs/2506.02019)) | Structured dictionary/BC knowledge base plus an error locator | 82.1% of 315 cases |
| **NL2FOAM** ([2504.09602](https://arxiv.org/abs/2504.09602)) | Fine-tuned 7B model plus a correction loop | 88.7% |
| **Coding-agent study** ([2602.11689](https://arxiv.org/abs/2602.11689)) | A generic coding agent with an OpenFOAM-specific system prompt | Tutorial-derived cases went from 4/9 to 9/9 |

**What drives success:** retrieval of the closest tutorial plus an error-log correction loop. Removing the loop alone cost Foam-Agent 36 points.
**Unsolved:** silent physics errors (a case runs but gives wrong physics), 3D meshing, and stiff cases.

**Practical setup:**
- Use ESI **OpenFOAM v2606** through the `opencfd/openfoam-default` Docker image.
- Use **foamlib** for case editing and running; prefer it over PyFoam.
- Pin a single distribution. The openfoam.org line (v13/v14) restructured its solvers.
- On Windows, keep cases inside the WSL/Docker filesystem rather than `/mnt/c`.

---

## 3. Agents + FEA

| System | Notes |
|---|---|
| **FEABench** ([2504.06260](https://arxiv.org/abs/2504.06260)) | Agent drives COMSOL. 88% of its API calls executed, but 0 problems were fully solved. Executing is not the same as being correct. |
| **FEM-Bench** ([2512.20732](https://arxiv.org/abs/2512.20732)) | 33 graduate-level problems on writing FE code |
| **AutoFEA** (AAAI'25), **FeaGPT** ([2510.21993](https://arxiv.org/abs/2510.21993)), [2604.06788](https://arxiv.org/abs/2604.06788) | Agents that generate CalculiX `.inp` decks: geometry → Gmsh → ccx → check results |
| **MooseAgent** ([2504.08621](https://arxiv.org/abs/2504.08621)) | LangGraph + RAG over MOOSE input cards, about 93% |
| **ALL-FEM** ([2603.21011](https://arxiv.org/abs/2603.21011)) | Fine-tuned models that write FEniCS code |

### Open-source solver choice
- **CalculiX (primary).**
  - Abaqus-style text decks, which LLMs know well and which are easy to diff.
  - Ships as a single binary for Windows and Linux.
  - Covers static, contact, plasticity, modal, buckling and thermal analysis.
  - Toolchain: gmsh → .inp → ccx → .frd/.dat → ccx2paraview/meshio → PyVista. PrePoMax for checking results by eye.
- **FEniCSx (secondary):** for custom PDEs and multiphysics; run it in Docker.
- **scikit-fem:** pure-Python, independent cross-check solutions.
- **Code_Aster, MOOSE, Elmer:** optional later. They are heavy to set up or have weak Python scripting.
- **Meshing:** Gmsh Python API (`pip install gmsh`), Netgen, snappyHexMesh, cfMesh.
- **Post-processing:** meshio, PyVista (off-screen PNG rendering for VLM feedback), pvbatch.

---

## 4. Benchmarks and evaluation

| Benchmark | Domain | Grading |
|---|---|---|
| FEABench | COMSOL FEA | Numeric tolerance on the target quantity |
| **EngDesign** ([2509.16204](https://arxiv.org/abs/2509.16204)) | Open-ended design across 9 domains | **Simulation-verified functional requirements** with partial credit |
| **CFDLLMBench / FoamBench** ([2509.20374](https://arxiv.org/abs/2509.20374)) | OpenFOAM | Case executes, plus comparison of fields against a reference. Has an "Advanced" split of non-tutorial tasks. |
| SimBench ([2408.11987](https://arxiv.org/abs/2408.11987)) | PyChrono | Fine-tuned LLM judge |
| Text2CAD, CADPrompt, CADBench, Text2CAD-Bench | CAD generation | Chamfer distance, IoU, invalidity |
| **CADTests** ([2605.07807](https://arxiv.org/abs/2605.07807)) | CAD | **Executable boolean B-rep tests** (topology counts, bounding box, volume). These handle ambiguous prompts better than Chamfer distance. |
| **MUSE** ([2605.28579](https://arxiv.org/abs/2605.28579)) | Multi-part assemblies | Code → geometry → VLM rubric (manufacturability, assemblability) |
| CAD-bench | CAD | 179 tasks in 4 tiers. Best agent about 68%; functional-intent tasks near 0% |
| DesignQA, MechVQA, SoM-1K, PhysicsEval | Knowledge, drawings, problem sets | Accuracy / F1 |
| MecEng ([2608.14615](https://arxiv.org/abs/2608.14615)) | Mechanical and multibody simulation | Automated *(verify)* |
| **EngiBench** ([2508.00831](https://arxiv.org/abs/2508.00831)) | Containerized design-optimization simulators | Reusable as verifiers |

**Gap:** nothing yet looks like SWE-bench for mechanical engineering: multi-step tasks across a real CAD → mesh → FEA/CFD toolchain, run in containers and graded by hidden, physics-verified tests. That gap is the opportunity for this project.

### Harness and eval infrastructure
- **Harbor / Terminal-Bench 2.0 task format** ([harborframework.com](https://harborframework.com/docs/tasks)). Each task contains:
  - `instruction.md`
  - `task.toml`
  - `environment/Dockerfile`
  - `solution/solve.sh` (the oracle solution)
  - `tests/test.sh` (hidden, mounted only at verification time, writes a reward)

  Using this format makes any agent pluggable.
- **Inspect AI** (UK AISI): Dataset + Solver + Scorer. Provides Docker sandboxes, epochs/pass@k, token and cost logging, and a log viewer.
- **Agent frameworks:** Claude Agent SDK, OpenAI Agents SDK, LangGraph, smolagents.
- **Metrics:**
  - pass@1 averaged over 5 or more runs, with confidence intervals
  - pass@k and pass^k
  - partial credit
  - cost-normalized score
  - a breakdown of failures by stage
