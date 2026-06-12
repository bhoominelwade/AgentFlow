import os

import google.generativeai as genai

from src.providers import ProviderResponse


async def complete(prompt: str, model: str) -> ProviderResponse:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    gemini = genai.GenerativeModel(model)
    response = await gemini.generate_content_async(prompt)
    usage = response.usage_metadata
    return ProviderResponse(
        output=response.text,
        tokens_in=usage.prompt_token_count,
        tokens_out=usage.candidates_token_count,
        done=True,
    )
