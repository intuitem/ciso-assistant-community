"""
Aggregate chat memory metrics from `ChatMessage.metrics`.

Usage:
    python manage.py chat_metrics --since 24h
    python manage.py chat_metrics --since 7d --top 5
    python manage.py chat_metrics --since 30d --json
"""

import json
import re
from collections import defaultdict
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from chat.models import ChatMessage


_SINCE_RE = re.compile(r"^(\d+)([hdwm])$")


def parse_since(s: str) -> timedelta:
    """Parse '24h', '7d', '4w', '6m' → timedelta. Months treated as 30 days."""
    m = _SINCE_RE.match(s.strip().lower())
    if not m:
        raise CommandError(
            f"Invalid --since value '{s}'. Use forms like '24h', '7d', '4w', '6m'."
        )
    n, unit = int(m.group(1)), m.group(2)
    if n <= 0:
        raise CommandError("--since must be positive")
    return {
        "h": timedelta(hours=n),
        "d": timedelta(days=n),
        "w": timedelta(weeks=n),
        "m": timedelta(days=30 * n),
    }[unit]


def percentile(values: list[int], p: float) -> int:
    """Linear-interpolation percentile. Returns 0 for an empty input."""
    if not values:
        return 0
    s = sorted(values)
    if len(s) == 1:
        return s[0]
    k = (len(s) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(s) - 1)
    if lo == hi:
        return s[lo]
    return int(s[lo] + (s[hi] - s[lo]) * (k - lo))


class Command(BaseCommand):
    help = "Aggregate chat memory metrics over a time window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--since",
            default="24h",
            help="Time window: 24h / 7d / 4w / 6m (default: 24h)",
        )
        parser.add_argument(
            "--top",
            type=int,
            default=5,
            help="Show top N sessions by avg prompt tokens (default: 5)",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit aggregate as JSON instead of a human report",
        )

    def handle(self, *args, **opts):
        delta = parse_since(opts["since"])
        cutoff = timezone.now() - delta

        qs = (
            ChatMessage.objects.filter(role="assistant", created_at__gte=cutoff)
            .exclude(metrics__isnull=True)
            .values("session_id", "metrics", "created_at")
        )

        prompt_tokens: list[int] = []
        over_budget = 0
        high_watermark = 0
        per_session: dict[str, list[int]] = defaultdict(list)
        sessions_seen: set[str] = set()
        model_ctx_values: set[int] = set()

        for row in qs:
            m = row["metrics"] or {}
            pt = int(m.get("prompt_tokens", 0))
            if pt <= 0:
                continue
            prompt_tokens.append(pt)
            if m.get("over_budget"):
                over_budget += 1
            if m.get("high_watermark"):
                high_watermark += 1
            sid = str(row["session_id"])
            per_session[sid].append(pt)
            sessions_seen.add(sid)
            mc = int(m.get("model_context_tokens", 0) or 0)
            if mc:
                model_ctx_values.add(mc)

        turns = len(prompt_tokens)
        # Use max so utilization% is anchored to the largest observed capacity
        # (deterministic regardless of iteration order)
        model_ctx = max(model_ctx_values, default=0)

        agg = {
            "since": opts["since"],
            "turns": turns,
            "sessions": len(sessions_seen),
            "p50_tokens": percentile(prompt_tokens, 0.50),
            "p95_tokens": percentile(prompt_tokens, 0.95),
            "p99_tokens": percentile(prompt_tokens, 0.99),
            "max_tokens": max(prompt_tokens) if prompt_tokens else 0,
            "model_context_tokens": model_ctx,
            "over_budget_turns": over_budget,
            "over_budget_pct": (round(100 * over_budget / turns, 2) if turns else 0.0),
            "high_watermark_turns": high_watermark,
            "high_watermark_pct": (
                round(100 * high_watermark / turns, 2) if turns else 0.0
            ),
            "top_sessions": [
                {
                    "session_id": sid,
                    "turns": len(vals),
                    "avg_tokens": int(sum(vals) / len(vals)),
                    "max_tokens": max(vals),
                }
                for sid, vals in sorted(
                    per_session.items(),
                    key=lambda kv: sum(kv[1]) / len(kv[1]),
                    reverse=True,
                )[: opts["top"]]
            ],
        }

        if opts["json"]:
            self.stdout.write(json.dumps(agg, indent=2))
            return

        self._print_report(agg)

    def _print_report(self, agg: dict) -> None:
        out = self.stdout.write
        out("========== Chat Memory Metrics ==========")
        out(f"Window:                  last {agg['since']}")
        out(f"Turns analyzed:          {agg['turns']}")
        out(f"Sessions touched:        {agg['sessions']}")

        if not agg["turns"]:
            out("No data in window.")
            return

        ctx = agg["model_context_tokens"] or 1
        out("Token utilization:")
        for label, key in (
            ("p50", "p50_tokens"),
            ("p95", "p95_tokens"),
            ("p99", "p99_tokens"),
            ("max", "max_tokens"),
        ):
            v = agg[key]
            out(f"  {label}:  {v:>6,d} tokens  ({100 * v / ctx:5.1f}%)")

        out(
            f"Over budget:             {agg['over_budget_turns']:>4d} turns "
            f"({agg['over_budget_pct']:.2f}%)"
        )
        out(
            f"High watermark hits:     {agg['high_watermark_turns']:>4d} turns "
            f"({agg['high_watermark_pct']:.2f}%)"
        )
        out(f"Model context (configured): {agg['model_context_tokens']:,d}")

        if agg["top_sessions"]:
            out("")
            out(f"Top {len(agg['top_sessions'])} sessions by avg prompt tokens:")
            for s in agg["top_sessions"]:
                out(
                    f"  {s['session_id'][:8]}…  "
                    f"{s['turns']:>3d} turns  "
                    f"avg {s['avg_tokens']:>5,d}  "
                    f"max {s['max_tokens']:>5,d}"
                )
