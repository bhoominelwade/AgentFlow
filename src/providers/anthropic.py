import os

from anthropic import AsyncAnthropic

from src.providers import ProviderResponse


async def complete(prompt: str, model: str) -> ProviderResponse:
    client = AsyncAnthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    message = await client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return ProviderResponse(
        output=message.content[0].text,
        tokens_in=message.usage.input_tokens,
        tokens_out=message.usage.output_tokens,
        done=True,
    )
