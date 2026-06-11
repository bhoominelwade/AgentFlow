from dataclasses import dataclass


@dataclass
class ProviderResponse:
    output: str
    tokens_in: int
    tokens_out: int
    done: bool
