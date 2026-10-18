"""Unit tests for patch prompt building and model adapters (Phase 2)."""

from __future__ import annotations

import io
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from tracefix.repair.interfaces import RepairConfig
from tracefix.repair.patch_generator import (
    FatalProviderError,
    HttpModelProvider,
    MockModelProvider,
    PatchPromptBuilder,
    TransientProviderError,
)


def test_prompt_builder_includes_report_and_context() -> None:
    builder = PatchPromptBuilder()
    context_manifest = {
        "items": [
            {
                "file_path": "requests/models.py",
                "symbol": "PreparedRequest.prepare_content_length",
                "content": "def prepare_content_length(self):\n    pass\n",
                "expansion_explanation": "2-hop callers",
            }
        ]
    }
    prompt = builder.build(
        bug_report="GET request sends content-length header",
        context_manifest=context_manifest,
    )
    assert "GET request sends content-length header" in prompt
    assert "requests/models.py" in prompt
    assert "PreparedRequest.prepare_content_length" in prompt
    assert "2-hop callers" in prompt
    assert "diff --git" in prompt


def test_mock_provider_records_calls_and_queues() -> None:
    provider = MockModelProvider()
    resp1 = "diff 1"
    resp2 = "diff 2"
    provider.queue_response(resp1)
    provider.queue_response(resp2)

    config = RepairConfig()
    out1 = provider.generate_patch("prompt 1", config)
    out2 = provider.generate_patch("prompt 2", config)

    assert out1 == "diff 1"
    assert out2 == "diff 2"
    assert len(provider.call_history) == 2
    assert provider.call_history[0]["prompt"] == "prompt 1"


def test_http_provider_missing_key_raises_fatal() -> None:
    provider = HttpModelProvider(api_key="")
    config = RepairConfig()
    with pytest.raises(FatalProviderError, match="Missing API key"):
        provider.generate_patch("test prompt", config)


@patch("urllib.request.urlopen")
def test_http_provider_success(mock_urlopen: MagicMock) -> None:
    mock_resp = MagicMock()
    mock_resp.read.return_value = (
        b'{"choices": [{"message": {"content": "```diff\\n+++ b/a.py\\n```"}}]}'
    )
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    provider = HttpModelProvider(api_key="sk-test-key", base_url="https://fake.ai/api")
    config = RepairConfig(model_name="test-model")
    res = provider.generate_patch("prompt text", config)
    assert "+++ b/a.py" in res


@patch("urllib.request.urlopen")
def test_http_provider_maps_429_to_transient(mock_urlopen: MagicMock) -> None:
    err = urllib.error.HTTPError(
        url="https://fake.ai/api",
        code=429,
        msg="Too Many Requests",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b"Rate limit exceeded"),
    )
    mock_urlopen.side_effect = err

    provider = HttpModelProvider(api_key="sk-test", base_url="https://fake.ai/api")
    config = RepairConfig()
    with pytest.raises(TransientProviderError, match="HTTP 429"):
        provider.generate_patch("prompt", config)


@patch("urllib.request.urlopen")
def test_http_provider_maps_401_to_fatal(mock_urlopen: MagicMock) -> None:
    err = urllib.error.HTTPError(
        url="https://fake.ai/api",
        code=401,
        msg="Unauthorized",
        hdrs=None,  # type: ignore[arg-type]
        fp=io.BytesIO(b"Invalid API key"),
    )
    mock_urlopen.side_effect = err

    provider = HttpModelProvider(api_key="sk-test", base_url="https://fake.ai/api")
    config = RepairConfig()
    with pytest.raises(FatalProviderError, match="HTTP 401"):
        provider.generate_patch("prompt", config)


@patch("urllib.request.urlopen")
def test_http_provider_maps_timeout_to_transient(mock_urlopen: MagicMock) -> None:
    mock_urlopen.side_effect = TimeoutError("Connection timed out")

    provider = HttpModelProvider(api_key="sk-test", base_url="https://fake.ai/api")
    config = RepairConfig()
    with pytest.raises(TransientProviderError, match="timeout"):
        provider.generate_patch("prompt", config)
