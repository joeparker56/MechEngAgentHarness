"""Plumbing-check agent for Harbor. Makes no LLM calls.

It proves the external-agent path works end to end: Harbor imports this class from the host
env, starts the task container, and the agent drives the container via `environment.exec`.
It records the tool inventory but does not attempt the task, so it should score 0.

    uv run harbor run -p bench/tasks/t1/cantilever-tip-deflection \
        -a mecheng_agent.stub_agent:StubAgent
"""

from __future__ import annotations

import json

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment
from harbor.models.agent.context import AgentContext


class StubAgent(BaseAgent):
    @staticmethod
    def name() -> str:
        return "mecheng-stub"

    def version(self) -> str | None:
        return "0.1.0"

    async def setup(self, environment: BaseEnvironment) -> None:
        pass

    async def run(
        self,
        instruction: str,
        environment: BaseEnvironment,
        context: AgentContext,
    ) -> None:
        result = await environment.exec(command="mecheng info")
        record = {
            "instruction_chars": len(instruction),
            "exec_return_code": result.return_code,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        (self.logs_dir / "stub_agent.json").write_text(json.dumps(record, indent=2))
