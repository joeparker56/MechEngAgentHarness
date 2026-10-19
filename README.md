# MechEng Agent Harness

An agent harness for mechanical engineering design (CAD → mesh → FEA/CFD) and a private
benchmark of engineering tasks with physics-verified grading. See [PLAN.md](PLAN.md) and
[RESEARCH.md](RESEARCH.md).

## Layout

| Path | Contents |
|---|---|
| `src/mecheng/` | Engineering tool library + `mecheng` CLI. Runs **inside** task containers. |
| `src/mecheng_agent/` | Host-side agents, wrapped as Harbor external agents (`BaseAgent`). |
| `docker/` | Task images: `mecheng-base` (CAD/mesh/render), `mecheng-fea` (+ CalculiX). |
| `bench/tasks/` | Benchmark tasks in Harbor format. |
| `bench/references/` | Convergence studies and reference values behind each grader. |
| `scripts/dev.py` | Build / test / smoke task runner. |
| `tests/` | Host unit tests. |

## Quick start (Windows host, Docker Desktop running)

```powershell
uv sync                                   # host env: harbor, langgraph, pytest
uv run python scripts/dev.py build        # build mecheng-base:dev and mecheng-fea:dev
uv run python scripts/dev.py test         # unit tests
uv run python scripts/dev.py smoke        # CAD -> gmsh -> CalculiX -> PNG, output in out/smoke/
```

## Running benchmark tasks with Harbor

Set `PYTHONIOENCODING=utf-8` first. Harbor's console output can fail on Windows otherwise.

```powershell
$env:PYTHONIOENCODING = "utf-8"
$task = "bench/tasks/t1/cantilever-tip-deflection"
uv run harbor run -p $task -a oracle -o jobs -y                         # reference solution, should score 1
uv run harbor run -p $task -a oracle --ae SOLUTION=wrong -o jobs -y     # flawed solution, should score 0
uv run harbor run -p $task -a mecheng_agent.stub_agent:StubAgent -o jobs -y
uv run harbor view jobs
```

## Authoring a task

Each task is a directory with the following files:
- `instruction.md`
- `task.toml`, which sets `docker_image = "mecheng-fea:dev"` and uses a separate verifier
- `environment/`, which must exist even when using a prebuilt image
- `solution/solve.sh`, plus a `SOLUTION=wrong` variant
- `tests/test.sh` and `tests/grade.py`

`reward.json` may contain **only numeric values**. Put text diagnostics in `details.json`.
List agent outputs in `artifacts` so the separate verifier receives them.
