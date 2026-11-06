#!/usr/bin/env python3
"""Live check that every curated Planly resource link opens. Run: backend/venv/bin/python scripts/verify_plan_resources.py"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.plans import resources as R  # noqa: E402

urls = sorted(R._curated_urls())
res = asyncio.run(R.verify(urls))
bad = [u for u in urls if not res.get(u)]
print(f"{len(urls)} curated links, {len(bad)} unreachable")
for u in bad:
    print("  BAD", u)
sys.exit(1 if bad else 0)
