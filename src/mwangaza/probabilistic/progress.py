from __future__ import annotations

import time


class EtaProgress:
    def __init__(self, label: str, *, percent_step: int = 5) -> None:
        self.label = label
        self.percent_step = percent_step
        self.started = time.monotonic()
        self.initial_completed: int | None = None
        self.last_bucket = -1
        self.last_printed = self.started

    def __call__(self, completed: int, total: int) -> None:
        if self.initial_completed is None:
            self.initial_completed = completed
        elapsed = max(0.001, time.monotonic() - self.started)
        new_completed = max(0, completed - self.initial_completed)
        remaining = max(0, total - completed)
        rate = new_completed / elapsed
        eta = remaining / rate if rate > 0 else None
        percent = 100.0 if total == 0 else completed / total * 100
        bucket = int(percent // self.percent_step)
        now = time.monotonic()
        if (
            completed not in {0, total}
            and bucket <= self.last_bucket
            and now - self.last_printed < 5
        ):
            return
        self.last_bucket = bucket
        self.last_printed = now
        eta_text = _duration(eta) if eta is not None else "calculando..."
        print(
            f"[{self.label}] {completed}/{total} ({percent:5.1f}%) "
            f"| ETA {eta_text}",
            flush=True,
        )


def _duration(seconds: float | None) -> str:
    if seconds is None:
        return "calculando..."
    rounded = max(0, int(round(seconds)))
    minutes, secs = divmod(rounded, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"
