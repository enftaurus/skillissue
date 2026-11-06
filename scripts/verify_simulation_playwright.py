#!/usr/bin/env python3
"""
End-to-end: candidate starts the Uber hiring simulation from Company Tracks, solves both OA problems, submits the
project round, answers the AI interviewer, and reads the practice report.

    SKILLISSUE_EVAL_EMAIL=... SKILLISSUE_EVAL_PASSWORD=... backend/venv/bin/python scripts/verify_simulation_playwright.py
"""
import os
import re
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

WEB = os.environ.get("SKILLISSUE_WEB", "http://localhost:5173")
OUT = Path(__file__).resolve().parents[1] / "artifacts_e2e" / "simulation"
OUT.mkdir(parents=True, exist_ok=True)

ISLANDS = """import sys
def main():
    d = sys.stdin.read().split()
    r, c = int(d[0]), int(d[1]); g = [d[2 + i*c: 2 + (i+1)*c] for i in range(r)]
    seen = set(); n = 0
    for i in range(r):
        for j in range(c):
            if g[i][j] == '1' and (i, j) not in seen:
                n += 1; stack = [(i, j)]; seen.add((i, j))
                while stack:
                    x, y = stack.pop()
                    for a, b in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                        if 0 <= a < r and 0 <= b < c and g[a][b] == '1' and (a, b) not in seen:
                            seen.add((a, b)); stack.append((a, b))
    print(n)
main()
"""
COURSES = """import sys
from collections import deque
def main():
    d = list(map(int, sys.stdin.read().split()))
    n, p = d[0], d[1]; adj = [[] for _ in range(n)]; indeg = [0]*n
    for k in range(p):
        a, b = d[2+2*k], d[3+2*k]; adj[b].append(a); indeg[a] += 1
    q = deque(i for i in range(n) if indeg[i] == 0); done = 0
    while q:
        u = q.popleft(); done += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0: q.append(v)
    print('true' if done == n else 'false')
main()
"""
ANSWERS = [
    "For islands I used iterative DFS with an explicit stack and a visited set: O(R*C) time and space. Iterative so deep grids don't blow the recursion limit.",
    "Course schedule is Kahn's algorithm: build in-degrees, BFS from zero in-degree nodes, and if I processed fewer than n courses there's a cycle. O(V+E).",
    "For a rate limiter shared across instances I'd keep token buckets in Redis and refill lazily on read using a Lua script so check-and-decrement is atomic.",
    "If Redis is down I'd fail open for low-risk endpoints with a local in-memory bucket and fail closed for payments, and alert on the fallback rate.",
    "I'd measure p99 latency of the limiter call and the rejection rate per client, and load test with a replay of production traffic before rollout.",
]
findings = []


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        findings.append(msg)


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def set_monaco(page, code):
    page.wait_for_function("window.monaco && window.monaco.editor.getModels().length > 0", timeout=30000)
    page.evaluate("code => window.monaco.editor.getModels()[0].setValue(code)", code)


def main():
    email, pw = os.environ.get("SKILLISSUE_EVAL_EMAIL"), os.environ.get("SKILLISSUE_EVAL_PASSWORD")
    if not email:
        sys.exit("Set SKILLISSUE_EVAL_EMAIL / SKILLISSUE_EVAL_PASSWORD.")
    errors = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_context(viewport={"width": 1400, "height": 950}).new_page()
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(f"{WEB}/login")
        pg.fill("#email-address-or-username", email)
        pg.fill("input[type=password]", pw)
        pg.get_by_role("button", name=re.compile("sign in", re.I)).click()
        pg.wait_for_timeout(1500)
        pg.goto(f"{WEB}/tracks")
        pg.get_by_role("button", name=re.compile("Hiring Simulations")).click()
        expect(pg.get_by_text("Number of Islands · Course Schedule")).to_be_visible(timeout=15000)
        shot(pg, "01_simulations")
        pg.get_by_role("button", name=re.compile("Start Uber simulation")).click()
        pg.wait_for_url(re.compile(r"/assess/take/"), timeout=20000)

        # OA: two problems
        expect(pg.get_by_role("button", name="Problem 2")).to_be_visible(timeout=20000)
        set_monaco(pg, ISLANDS)
        pg.get_by_role("button", name=re.compile("Run sample tests")).click()
        expect(pg.get_by_text(re.compile("Sample 1"))).to_be_visible(timeout=30000)
        check(pg.locator(".text-emerald-700").count() > 0 and pg.locator(".text-rose-700").count() == 0, "islands passes samples")
        pg.get_by_role("button", name="Problem 2").click()
        pg.wait_for_timeout(500)
        set_monaco(pg, COURSES)
        pg.get_by_role("button", name=re.compile("Run sample tests")).click()
        expect(pg.get_by_text(re.compile("Sample 1"))).to_be_visible(timeout=30000)
        shot(pg, "02_oa")
        pg.get_by_role("button", name="Problem 1").click()
        pg.wait_for_timeout(500)
        check("seen = set()" in pg.evaluate("window.monaco.editor.getModels()[0].getValue()"), "problem 1 code kept after switching tabs")
        pg.get_by_role("button", name=re.compile("Submit round")).click()
        pg.get_by_role("button", name=re.compile("Yes, submit")).click()

        expect(pg.get_by_text("Post-Submission Cross-Examination")).to_be_visible(timeout=60000)
        for text in ANSWERS[:3]:
            box = pg.locator("textarea[placeholder^='Explain']")
            try:
                box.wait_for(state="visible", timeout=60000)
            except Exception:
                break
            box.fill(text)
            pg.get_by_role("button", name=re.compile("Next Question|Submit All Explanations")).click()
            pg.wait_for_timeout(800)
        try:
            pg.get_by_role("button", name=re.compile("Proceed to Next Round")).click(timeout=90000)
        except Exception:
            shot(pg, "02b_explanation_stuck")
            print("BODY:", pg.inner_text("body")[:1500])
            print("console:", errors[-5:])
            raise

        # Project round
        expect(pg.get_by_role("button", name=re.compile("Run tests"))).to_be_visible(timeout=30000)
        pg.get_by_role("button", name=re.compile("Run tests")).click()
        expect(pg.get_by_text(re.compile(r"\d+ passed · \d+ failed"))).to_be_visible(timeout=60000)
        shot(pg, "03_project")
        pg.get_by_role("button", name=re.compile("Submit round")).click()
        pg.get_by_role("button", name=re.compile("Yes, submit")).click()

        # Interview
        expect(pg.get_by_text(re.compile("The interviewer may ask"))).to_be_visible(timeout=90000)
        for text in ANSWERS:
            if not pg.get_by_placeholder("Your answer").count():
                break
            pg.get_by_placeholder("Your answer").fill(text)
            pg.get_by_role("button", name=re.compile("^Send")).click()
            pg.wait_for_timeout(500)
            pg.wait_for_function("!document.body.innerText.includes('Sending...')", timeout=90000)
        qs = pg.locator(".rounded-tl-sm").all_inner_texts()
        print("interviewer:", *qs, sep="\n  - ")
        check(len(qs) == 5 and len(set(qs)) == 5, "5 distinct interview questions")
        check(not any(re.search(r"\b(I work at|here at) Uber\b", q) for q in qs), "interviewer never claims to work at Uber")
        shot(pg, "04_interview")
        pg.get_by_role("button", name=re.compile("Finish assessment")).click()
        pg.get_by_role("button", name=re.compile("Yes, submit")).click()

        expect(pg.get_by_text("Simulation report")).to_be_visible(timeout=120000)
        pg.wait_for_timeout(1500)
        shot(pg, "05_report")
        body = pg.inner_text("body")
        check("2/2 hidden tests" in body or re.search(r"number-of-islands: \d+/\d+ hidden tests", body) is not None, "OA hidden-test results in report")
        check("repository tests passed" in body, "project test results in report")
        print("report excerpt:\n", body[body.find("Simulation report"):][:1500])
        b.close()
    errs = [e for e in errors if "favicon" not in e]
    check(not errs, f"no console errors {errs[:2]}")
    print(f"\n{len(findings)} findings. Screenshots in {OUT}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
