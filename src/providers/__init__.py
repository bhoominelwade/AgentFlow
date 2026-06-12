from dataclasses import dataclass


@dataclass
class ProviderResponse:
    output: str
    tokens_in: int
    tokens_out: int
    done: bool


def provider_for_model(model: str) -> str:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt"):
        return "openai"
    if model.startswith("gemini"):
        return "gemini"
    raise ValueError(f"No provider for model '{model}'")


async def complete(prompt: str, model: str) -> ProviderResponse:
    from dotenv import load_dotenv

    load_dotenv()
    name = provider_for_model(model)
    if name == "anthropic":
        from src.providers import anthropic as provider
    elif name == "openai":
        from src.providers import openai as provider
    else:
        from src.providers import gemini as provider
    return await provider.complete(prompt, model)
