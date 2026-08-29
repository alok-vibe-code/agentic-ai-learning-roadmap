"""CLI and deterministic resilience scenarios."""

from __future__ import annotations

import argparse
import json

from agent import ProductionHardenedAgent
from config import load_config
from service import ScriptedProvider
from telemetry import StructuredLogger


class DemoClock:
    def __init__(self, value: float = 1000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value

    def sleep(self, ms: int) -> None:
        self.value += ms

    def advance(self, ms: int) -> None:
        self.value += ms


def render(result) -> None:
    print(json.dumps({
        "status": result.status,
        "text": result.text,
        "trace_id": result.trace_id,
        "provider": result.provider,
        "degraded": result.degraded,
        "cache_status": result.cache_status,
        "sources": list(result.sources),
        "attempts": [record.__dict__ for record in result.attempts],
        "metadata": result.metadata,
    }, indent=2, ensure_ascii=False))


def make_agent(primary_script, fallback_script, clock, *, echo=False):
    config = load_config()
    return ProductionHardenedAgent(
        config=config,
        primary=ScriptedProvider(config.primary_provider, script=primary_script),
        fallback=ScriptedProvider(
            config.fallback_provider,
            script=fallback_script,
            estimated_tokens=90,
            simulated_cost_usd=0.0002,
        ),
        clock_ms=clock,
        sleeper_ms=clock.sleep,
        random_fn=lambda: 0.5,
        logger=StructuredLogger(echo=echo),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the Week 12 production-hardening demo."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask = sub.add_parser("ask")
    ask.add_argument("query")
    ask.add_argument("--principal", default="demo-user")
    ask.add_argument("--trace", action="store_true")

    demo = sub.add_parser("demo")
    demo.add_argument(
        "scenario",
        choices=[
            "success",
            "retry",
            "fallback",
            "cache",
            "stale",
            "circuit",
            "unavailable",
        ],
    )
    demo.add_argument("--trace", action="store_true")

    sub.add_parser("health")

    args = parser.parse_args()
    clock = DemoClock()

    if args.command == "ask":
        agent = make_agent(["success"], ["success"], clock, echo=args.trace)
        result = agent.answer(args.principal, args.query)
        render(result)
        return 0 if result.status == "ok" else 1

    if args.command == "health":
        agent = make_agent(["success"], ["success"], clock)
        print(json.dumps(agent.health().__dict__, indent=2))
        return 0

    if args.scenario == "success":
        agent = make_agent(["success"], ["success"], clock, echo=args.trace)
        render(agent.answer("demo", "Explain circuit breakers"))
        return 0

    if args.scenario == "retry":
        agent = make_agent(
            ["transient", "timeout", "success"],
            ["success"],
            clock,
            echo=args.trace,
        )
        result = agent.answer("demo", "Explain retries and backoff")
        render(result)
        return 0 if result.status == "ok" and result.provider == "mock-primary" else 1

    if args.scenario == "fallback":
        agent = make_agent(
            ["permanent"],
            ["success"],
            clock,
            echo=args.trace,
        )
        result = agent.answer("demo", "Explain provider fallbacks")
        render(result)
        return 0 if result.status == "ok" and result.degraded else 1

    if args.scenario == "cache":
        agent = make_agent(["success"], ["success"], clock, echo=args.trace)
        render(agent.answer("demo", "Explain caching"))
        render(agent.answer("demo", "Explain caching"))
        return 0

    if args.scenario == "stale":
        agent = make_agent(["success"], ["success"], clock, echo=args.trace)
        first = agent.answer("demo", "Explain graceful degradation")
        render(first)

        clock.advance(agent.config.cache.ttl_ms + 1)
        agent.primary.script = ["permanent"]
        agent.primary.calls = 0
        agent.fallback.script = ["permanent"]
        agent.fallback.calls = 0

        stale = agent.answer("demo", "Explain graceful degradation")
        render(stale)
        return 0 if stale.status == "degraded" and stale.cache_status == "stale" else 1

    if args.scenario == "circuit":
        agent = make_agent(["transient"], ["success"], clock, echo=args.trace)
        for index in range(3):
            result = agent.answer(f"demo-{index}", "Explain timeouts")
            render(result)
        print(json.dumps(agent.health().__dict__, indent=2))
        return 0

    if args.scenario == "unavailable":
        agent = make_agent(["permanent"], ["permanent"], clock, echo=args.trace)
        result = agent.answer("demo", "Explain structured logging")
        render(result)
        return 0 if result.status == "unavailable" else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
