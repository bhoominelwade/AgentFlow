from src.providers import ProviderResponse


class MockProvider:
    def __init__(self, finish_after_steps: int = 1,
                 tokens_in_per_call: int = 10, tokens_out_per_call: int = 20):
        self.finish_after_steps = finish_after_steps
        self.tokens_in_per_call = tokens_in_per_call
        self.tokens_out_per_call = tokens_out_per_call
        self.calls = 0

    async def complete(self, prompt: str) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            output=f"[mock] response to: {prompt[:40]}",
            tokens_in=self.tokens_in_per_call,
            tokens_out=self.tokens_out_per_call,
            done=self.calls >= self.finish_after_steps,
        )
