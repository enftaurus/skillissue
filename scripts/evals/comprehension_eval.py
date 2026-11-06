#!/usr/bin/env python3
"""
Grader calibration for the code comprehension round (real LLM judge via the live API).

For every item and question it submits three synthetic answers and checks the grader orders them:
  strong  - built from the hidden key (expected output, bug line + key points, correct number)
  vague   - plausible-sounding but empty ("there might be an issue with the logic")
  wrong   - confident but blames the wrong line / wrong output
Reports accuracy per answer type and any inversions (vague or wrong scoring >= strong).

    export SKILLISSUE_EVAL_EMAIL=... SKILLISSUE_EVAL_PASSWORD=...
    backend/venv/bin/python scripts/evals/comprehension_eval.py
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.comprehension.bank import ITEMS  # noqa: E402

API = os.environ.get("SKILLISSUE_API", "http://localhost:8000/api/v1")
NUMERIC_ANSWERS = {("retry-helper", "q4"): "0.1 + 0.2 + 0.4 + 0.8 = 1.5 seconds",
                   ("async-fanout", "q1"): "About 2 seconds: 20 calls x 0.1s run sequentially.",
                   ("build-order", "q3"): "O(V + E)"}
WRONG_NUMERIC = {("retry-helper", "q4"): "3.1 seconds", ("async-fanout", "q1"): "0.2 seconds", ("build-order", "q3"): "O(V^2)"}


def strong(item, q):
    if q.type == "trace":
        return q.expected_output
    if q.type == "numeric":
        return NUMERIC_ANSWERS[(item.id, q.id)]
    text = ". ".join(q.key_points) + "."
    if q.type == "bug":
        lines = ", ".join(f"L{ln}" for _, ln in item.bug_lines())
        text = f"{lines}: " + text
    return text


def vague(item, q):
    return {"trace": "It prints some values.", "numeric": "It depends."}.get(
        q.type, "There might be an issue with the logic here; it could be improved with better design.")


def wrong(item, q):
    if q.type == "trace":
        return "Traceback (most recent call last): KeyError"
    if q.type == "numeric":
        return WRONG_NUMERIC[(item.id, q.id)]
    if q.type == "bug":
        return "L1: the import order is wrong, which breaks everything at scale."
    return "It's a standard sorting routine; nothing notable about it."


def main():
    email, password = os.environ.get("SKILLISSUE_EVAL_EMAIL"), os.environ.get("SKILLISSUE_EVAL_PASSWORD")
    if not email:
        sys.exit("Set SKILLISSUE_EVAL_EMAIL and SKILLISSUE_EVAL_PASSWORD.")
    c = httpx.Client(base_url=API, timeout=120)
    tok = c.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    c.headers["Authorization"] = f"Bearer {tok}"
    rows, inversions = [], []
    for item in ITEMS:
        sessions = {}
        for kind in ("strong", "vague", "wrong"):
            for _ in range(12):
                r = c.post("/comprehension/sessions", json={"item_id": item.id})
                if r.status_code != 429:
                    break
                time.sleep(10)
            sessions[kind] = r.json()["id"]
        for q in item.questions:
            scores = {}
            for kind, make in (("strong", strong), ("vague", vague), ("wrong", wrong)):
                for attempt in range(6):
                    r = c.post(f"/comprehension/sessions/{sessions[kind]}/answer", json={"question_id": q.id, "answer": make(item, q)})
                    if r.status_code != 429:
                        break
                    time.sleep(10)
                scores[kind] = r.json().get("score", 0.0) if r.status_code == 200 else None
            ok = scores["strong"] is not None and scores["strong"] >= 0.8 and (scores["vague"] or 0) < 0.35 and (scores["wrong"] or 0) < 0.35
            rows.append({"item": item.id, "q": q.id, "type": q.type, **scores, "ok": ok})
            if scores["strong"] is not None and max(scores["vague"] or 0, scores["wrong"] or 0) >= scores["strong"]:
                inversions.append((item.id, q.id, scores))
            print(f"{'ok ' if ok else 'BAD'} {item.id}/{q.id} ({q.type}) strong={scores['strong']} vague={scores['vague']} wrong={scores['wrong']}", flush=True)
        for sid in sessions.values():
            c.post(f"/comprehension/sessions/{sid}/finish")
    acc = sum(r["ok"] for r in rows) / len(rows)
    by_type = {}
    for r in rows:
        by_type.setdefault(r["type"], []).append(r["ok"])
    summary = {"questions": len(rows), "calibrated": round(acc, 2), "inversions": len(inversions),
               "by_type": {t: round(sum(v) / len(v), 2) for t, v in by_type.items()}}
    out = ROOT / "artifacts_e2e" / "evals" / f"comprehension-{datetime.now():%Y%m%d-%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"summary": summary, "rows": rows, "inversions": inversions}, indent=1))
    print(json.dumps(summary, indent=1))
    print("saved", out)


if __name__ == "__main__":
    main()
