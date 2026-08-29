"""Deterministic local provider adapters with failure injection."""

from __future__ import annotations

import json
from pathlib import Path

from errors import PermanentProviderError, ProviderTimeout, TransientProviderError
from models import ProviderResponse


DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parent / "data" / "knowledge.json"


class ScriptedProvider:
    """A local provider whose call outcomes can be scripted.

    Supported outcomes:
      success
      transient
      timeout
      permanent

    No network call or model API is used.
    """

    def __init__(
        self,
        name: str,
        *,
        script: list[str] | None = None,
        knowledge_path: str | Path | None = None,
        estimated_tokens: int = 120,
        simulated_cost_usd: float = 0.001,
        simulated_latency_ms: int = 25,
    ) -> None:
        self.name = name
        self.script = list(script or ["success"])
        self.estimated_tokens = estimated_tokens
        self.simulated_cost_usd = simulated_cost_usd
        self.simulated_latency_ms = simulated_latency_ms
        path = Path(knowledge_path) if knowledge_path else DEFAULT_KNOWLEDGE_PATH
        self.knowledge = json.loads(path.read_text(encoding="utf-8"))
        self.calls = 0

    def _next_outcome(self) -> str:
        if not self.script:
            return "success"
        index = min(self.calls, len(self.script) - 1)
        return self.script[index]

    def generate(self, query: str, *, timeout_ms: int) -> ProviderResponse:
        outcome = self._next_outcome()
        self.calls += 1

        if outcome == "transient":
            raise TransientProviderError(f"{self.name}: transient failure")
        if outcome == "permanent":
            raise PermanentProviderError(f"{self.name}: permanent failure")
        if outcome == "timeout" or self.simulated_latency_ms > timeout_ms:
            raise ProviderTimeout(
                f"{self.name}: attempt exceeded timeout of {timeout_ms} ms"
            )
        if outcome != "success":
            raise PermanentProviderError(
                f"{self.name}: unsupported scripted outcome {outcome!r}"
            )

        tokens = [
            token.strip(".,!?():;").casefold()
            for token in query.split()
            if len(token.strip(".,!?():;")) >= 4
        ]

        scored: list[tuple[int, str, str]] = []
        for source_id, text in self.knowledge.items():
            haystack = f"{source_id} {text}".casefold()
            score = sum(1 for token in tokens if token in haystack)
            if score:
                scored.append((score, source_id, text))

        scored.sort(key=lambda row: (-row[0], row[1]))
        selected = scored[:3]

        if not selected:
            answer = (
                "The local production-hardening knowledge base does not contain "
                "enough matching evidence for this query."
            )
            sources: tuple[str, ...] = ()
        else:
            answer = " ".join(text for _, _, text in selected)
            sources = tuple(source_id for _, source_id, _ in selected)

        return ProviderResponse(
            text=answer,
            provider=self.name,
            estimated_tokens=self.estimated_tokens,
            simulated_cost_usd=self.simulated_cost_usd,
            sources=sources,
        )
