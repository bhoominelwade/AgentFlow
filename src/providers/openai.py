import os

from openai import AsyncOpenAI

from src.providers import ProviderResponse


async def complete(prompt: str, model: str) -> ProviderResponse:
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    usage = response.usage
    return ProviderResponse(
        output=response.choices[0].message.content,
        tokens_in=usage.prompt_tokens,
        tokens_out=usage.completion_tokens,
        done=True,
    )
