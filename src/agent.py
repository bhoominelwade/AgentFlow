from dataclasses import dataclass, field

from src.models import AgentResult, Task


@dataclass
class ContextPacket:
    task: Task
    dependency_outputs: dict[str, str] = field(default_factory=dict)


class Agent:
    def __init__(self, provider, max_steps: int = 5):
        self.provider = provider
        self.max_steps = max_steps

    def _build_prompt(self, packet: ContextPacket) -> str:
        parts = [packet.task.description]
        for dep_id, output in packet.dependency_outputs.items():
            parts.append(f"Context from {dep_id}: {output}")
        return "\n\n".join(parts)

    async def run(self, context_packet: ContextPacket, model: str) -> AgentResult:
        prompt = self._build_prompt(context_packet)
        steps = 0
        tokens_in = 0
        tokens_out = 0
        output = ""
        hit_step_guard = False
        while True:
            if steps >= self.max_steps:
                hit_step_guard = True
                break
            response = await self.provider.complete(prompt, model)
            steps += 1
            tokens_in += response.tokens_in
            tokens_out += response.tokens_out
            output = response.output
            if response.done:
                break
        return AgentResult(
            task_id=context_packet.task.id,
            output=output,
            model_used=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            steps_taken=steps,
            hit_step_guard=hit_step_guard,
        )
