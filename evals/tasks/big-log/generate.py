"""Generate logs/app.log (~1.7 MB) deterministically into the run's workspace."""

import random

rng = random.Random(42)
levels = ["INFO"] * 12 + ["DEBUG"] * 6 + ["WARN"] * 2 + ["ERROR"]
lines = []
for i in range(24_000):
    level = rng.choice(levels)
    req = f"req-{rng.randrange(16**6):06x}"
    lines.append(f"2026-09-30T12:{i // 600 % 60:02d}:{i % 60:02d}Z {level:5} {req} handled /api/orders/{rng.randrange(10**5)} in {rng.randrange(900)}ms")
lines.insert(17_311, "2026-09-30T12:28:51Z FATAL req-7f3a9c payment ledger write failed: disk full")
(WORKSPACE / "logs" / "app.log").write_text("\n".join(lines) + "\n", encoding="utf-8")  # noqa: F821 — injected by the runner
