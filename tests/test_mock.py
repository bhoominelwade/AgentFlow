import pytest

from src.providers.mock import MockProvider


@pytest.mark.asyncio
async def test_mock_complete_returns_output_and_tokens():
    provider = MockProvider()
    resp = await provider.complete("hello")
    assert resp.output != ""
    assert resp.tokens_in == provider.tokens_in_per_call
    assert resp.tokens_out == provider.tokens_out_per_call
    assert resp.done is True


@pytest.mark.asyncio
async def test_mock_done_after_n_steps():
    provider = MockProvider(finish_after_steps=2)
    first = await provider.complete("x")
    assert first.done is False
    second = await provider.complete("x")
    assert second.done is True
