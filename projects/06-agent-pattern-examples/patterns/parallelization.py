"""Parallelization pattern: run independent tasks concurrently with failure isolation."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Iterable

from models import ParallelResult, PatternTrace


def default_worker(task: str) -> str:
    normalized = task.strip()
    if not normalized:
        raise ValueError("Task cannot be empty.")
    if normalized.casefold().startswith("fail:"):
        raise RuntimeError(normalized.split(":", 1)[1].strip() or "Requested failure")
    # Small deterministic delay makes concurrency visible without slowing the demo.
    time.sleep(0.01)
    return normalized.upper()


def run_parallel(
    tasks: list[str],
    worker: Callable[[str], object] = default_worker,
    max_workers: int = 4,
) -> tuple[list[ParallelResult], PatternTrace]:
    if not tasks:
        raise ValueError("At least one task is required.")
    if max_workers < 1:
        raise ValueError("max_workers must be >= 1.")

    trace = PatternTrace(pattern="parallelization")
    trace.add(
        1,
        "dispatch",
        task_count=len(tasks),
        max_workers=min(max_workers, len(tasks)),
    )

    results: list[ParallelResult | None] = [None] * len(tasks)

    with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as executor:
        future_map = {
            executor.submit(worker, task): (index, task)
            for index, task in enumerate(tasks)
        }

        for future in as_completed(future_map):
            index, task = future_map[future]
            try:
                value = future.result()
                results[index] = ParallelResult(
                    index=index,
                    task=task,
                    status="ok",
                    value=value,
                )
            except Exception as exc:
                results[index] = ParallelResult(
                    index=index,
                    task=task,
                    status="error",
                    error=f"{type(exc).__name__}: {exc}",
                )

    final_results = [result for result in results if result is not None]
    trace.add(
        2,
        "collect",
        successes=sum(result.status == "ok" for result in final_results),
        failures=sum(result.status == "error" for result in final_results),
        order_preserved=True,
    )
    trace.stop_reason = "all_tasks_settled"
    return final_results, trace
