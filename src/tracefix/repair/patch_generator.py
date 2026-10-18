"""Provider-independent patch generation and model adapters (Phase 2).

Complies with contracts/repair.json (C5).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from tracefix.repair.interfaces import (
    ModelProvider,
    PatchGenerationError,
    RepairConfig,
)


class TransientProviderError(PatchGenerationError):
    """Temporary provider failure eligible for retry (rate limit, 503, timeout)."""


class FatalProviderError(PatchGenerationError):
    """Permanent provider failure (invalid auth, malformed request, model not found)."""


class PatchPromptBuilder:
    """Constructs focused, structured prompts for model-guided patch generation."""

    def build(
        self,
        bug_report: str,
        context_manifest: dict[str, Any],
        max_context_tokens: int = 4000,
    ) -> str:
        """Assemble issue report, localized snippets, and unified diff instructions."""
        items = context_manifest.get("items", [])
        snippets: list[str] = []

        for item in items:
            path = item.get("file_path") or item.get("path") or "unknown"
            symbol = item.get("symbol") or ""
            content = item.get("content") or ""
            explanation = item.get("expansion_explanation") or ""

            header = f"### File: {path}"
            if symbol:
                header += f" | Symbol: {symbol}"
            if explanation:
                header += f" ({explanation})"

            snippets.append(f"{header}\n```python\n{content}\n```")

        context_body = "\n\n".join(snippets) if snippets else "No repository context provided."

        return (
            "You are an expert automated software repair engineer.\n"
            "Your task is to fix the reported bug by generating a standard unified diff.\n\n"
            "### Strict Output Requirements:\n"
            "1. Output ONLY a valid git unified diff (`diff --git a/... b/...`).\n"
            "2. Enclose the diff in a ```diff code block.\n"
            "3. Do NOT include conversational explanations, markdown notes, or justifications.\n"
            "4. Do NOT modify tests, CI files, or package configurations.\n"
            "5. Change only the necessary lines to resolve the issue.\n\n"
            f"### Bug Report / Issue Statement:\n{bug_report}\n\n"
            f"### Localized Code Context:\n{context_body}\n\n"
            "### Unified Diff Fix:\n"
        )


class MockModelProvider(ModelProvider):
    """Deterministic model provider for unit, contract, and offline tests."""

    def __init__(self, responses: list[str | Exception] | None = None) -> None:
        self.responses: list[str | Exception] = list(responses or [])
        self.call_history: list[dict[str, Any]] = []

    def queue_response(self, response: str | Exception) -> None:
        self.responses.append(response)

    def generate_patch(self, prompt: str, config: RepairConfig) -> str:
        self.call_history.append({"prompt": prompt, "config": config})
        if not self.responses:
            # Default minimal valid diff
            return (
                "```diff\n"
                "diff --git a/src/module.py b/src/module.py\n"
                "--- a/src/module.py\n"
                "+++ b/src/module.py\n"
                "@@ -10,1 +10,1 @@\n"
                "-    return False\n"
                "+    return True\n"
                "```"
            )

        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


class HttpModelProvider(ModelProvider):
    """Provider-independent HTTP model adapter using standard library urllib.

    Supports OpenAI, OpenRouter, and compatible chat completion endpoints
    without introducing heavy external SDK dependencies.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str = "anthropic/claude-3.5-sonnet",
    ) -> None:
        if api_key is not None:
            self.api_key = api_key
        else:
            self.api_key = (
                os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or ""
            )
        self.base_url = (
            base_url or os.environ.get("ANTHROPIC_BASE_URL") or "https://openrouter.ai/api/v1"
        ).rstrip("/")
        self.default_model = default_model

    def generate_patch(self, prompt: str, config: RepairConfig) -> str:
        if not self.api_key:
            raise FatalProviderError(
                "Missing API key. Set ANTHROPIC_API_KEY or configure model_provider."
            )

        # Normalize endpoint URL
        endpoint = (
            f"{self.base_url}/chat/completions"
            if not self.base_url.endswith("/chat/completions")
            else self.base_url
        )

        model_name = (
            config.model_name
            if config.model_name and config.model_name != "mock-fixer-v1"
            else self.default_model
        )

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an automated software repair engine. Output ONLY a valid git "
                        "unified diff enclosed in a ```diff code block. No explanations."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }

        body_bytes = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "TraceFix-RepairEngine/0.1.0",
        }

        req = urllib.request.Request(endpoint, data=body_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=config.timeout_seconds) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
                choices = resp_data.get("choices", [])
                if not choices:
                    raise FatalProviderError(
                        f"Empty completion choices returned by model {model_name}"
                    )
                content = choices[0].get("message", {}).get("content", "")
                return str(content)

        except urllib.error.HTTPError as err:
            status = err.code
            err_body = err.read().decode("utf-8", errors="replace")
            if status in {429, 500, 502, 503, 504}:
                raise TransientProviderError(
                    f"Transient HTTP {status} from model provider: {err_body}"
                ) from err
            raise FatalProviderError(
                f"Fatal HTTP {status} from model provider: {err_body}"
            ) from err

        except (urllib.error.URLError, TimeoutError) as err:
            raise TransientProviderError(
                f"Network or timeout error contacting model provider: {err}"
            ) from err
