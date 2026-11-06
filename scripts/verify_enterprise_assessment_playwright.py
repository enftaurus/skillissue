#!/usr/bin/env python3
"""
End-to-end: recruiter builds a drive in the UI -> signed-out candidate opens the invite, signs in, takes every round
-> candidate never sees a score -> recruiter's leaderboard ranks them.

    SKILLISSUE_EVAL_EMAIL=... SKILLISSUE_EVAL_PASSWORD=... backend/venv/bin/python scripts/verify_enterprise_assessment_playwright.py
"""
import os
import re
import sys
import uuid
from pathlib import Path

import httpx
from playwright.sync_api import expect, sync_playwright

WEB = os.environ.get("SKILLISSUE_WEB", "http://localhost:5173")
API = os.environ.get("SKILLISSUE_API", "http://localhost:8000/api/v1")
OUT = Path(__file__).resolve().parents[1] / "artifacts_e2e" / "enterprise"
OUT.mkdir(parents=True, exist_ok=True)

TWO_SUM = """import sys
def main():
    d = sys.stdin.read().split()
    n = int(d[0]); nums = list(map(int, d[1:n+1])); t = int(d[n+1])
    seen = {}
    for i, x in enumerate(nums):
        if t - x in seen:
            print(seen[t - x], i); return
        seen[x] = i
main()
"""
findings = []


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg, flush=True)
    if not cond:
        findings.append(msg)


def set_monaco(page, code):
    page.wait_for_function("window.monaco && window.monaco.editor.getModels().length > 0", timeout=30000)
    page.evaluate("code => window.monaco.editor.getModels()[0].setValue(code)", code)


def main():
    cand_email = os.environ.get("SKILLISSUE_EVAL_EMAIL")
    cand_pw = os.environ.get("SKILLISSUE_EVAL_PASSWORD")
    if not cand_email:
        sys.exit("Set SKILLISSUE_EVAL_EMAIL / SKILLISSUE_EVAL_PASSWORD (candidate account).")
    rec_email, rec_pw = f"recruiter_{uuid.uuid4().hex[:6]}@acme-e2e.dev", "Password123!"
    r = httpx.post(f"{API}/auth/register-recruiter", json={"organisation_name": "Acme E2E", "email": rec_email, "password": rec_pw})
    assert r.status_code == 201, r.text

    with sync_playwright() as p:
        browser = p.chromium.launch()
        console_errors = []

        # ---------------- recruiter creates the drive
        rec = browser.new_context(viewport={"width": 1400, "height": 950})
        rp = rec.new_page()
        rp.on("console", lambda m: console_errors.append(("recruiter", m.text)) if m.type == "error" else None)
        rp.goto(f"{WEB}/login")
        rp.fill("#email-address-or-username", rec_email)
        rp.fill("input[type=password]", rec_pw)
        rp.get_by_role("button", name=re.compile("sign in|log in", re.I)).click()
        rp.wait_for_url("**/enterprise", timeout=20000)
        rp.get_by_role("button", name=re.compile("new|create", re.I)).first.click()
        rp.get_by_placeholder(re.compile("Uber SDE-1", re.I)).fill("Acme Backend Drive (E2E)")
        rp.locator("textarea").first.fill("Backend services in Python: queues, caching, retries, and clean API design.")
        rp.get_by_label("Fixed problem").select_option("two-sum")
        rp.get_by_label("Problem count").select_option("1")
        rp.get_by_label("Code to read").select_option("retry-helper")
        rp.get_by_label("Questions").select_option("3")
        shot(rp, "01_recruiter_create_form")
        rp.get_by_role("button", name=re.compile("create pipeline", re.I)).click()
        rp.wait_for_timeout(1500)
        shot(rp, "02_recruiter_pipelines")
        tok = httpx.post(f"{API}/auth/login", json={"email": rec_email, "password": rec_pw}).json()["access_token"]
        pipes = httpx.get(f"{API}/enterprise/pipelines", headers={"Authorization": f"Bearer {tok}"}).json()
        pipe = next(x for x in pipes if x["title"] == "Acme Backend Drive (E2E)")
        types = [r["round_type"] for r in pipe["rounds"] if r["is_enabled"]]
        check(types == ["oa_dsa", "code_comprehension", "tough_interview"], f"drive created with rounds {types}")
        invite = f"{WEB}/assess/take/{pipe['invite_token']}"

        # ---------------- candidate: signed out -> landing -> sign in -> back
        cand = browser.new_context(viewport={"width": 1400, "height": 950})
        cp = cand.new_page()
        cp.on("console", lambda m: console_errors.append(("candidate", m.text)) if m.type == "error" else None)
        cp.goto(invite)
        expect(cp.get_by_text("Sign in to start")).to_be_visible(timeout=15000)
        shot(cp, "03_candidate_invite_signed_out")
        cp.get_by_text("Sign in to start").click()
        cp.fill("#email-address-or-username", cand_email)
        cp.fill("input[type=password]", cand_pw)
        cp.get_by_role("button", name=re.compile("sign in|log in", re.I)).click()
        cp.wait_for_url(re.compile(r"/assess/take/"), timeout=20000)
        check(pipe["invite_token"] in cp.url, "login returned the candidate to the invite link")
        cp.get_by_placeholder(re.compile("@")).fill("E2E Candidate")
        cp.get_by_role("button", name=re.compile("start or resume", re.I)).click()

        # ---------------- round 1: DSA
        expect(cp.get_by_role("button", name=re.compile("Run sample tests"))).to_be_visible(timeout=20000)
        check(cp.get_by_text(re.compile("Two Sum")).count() > 0, "server-assigned problem shown (Two Sum)")
        set_monaco(cp, TWO_SUM)
        cp.get_by_role("button", name=re.compile("Run sample tests")).click()
        expect(cp.get_by_text(re.compile("Sample 1"))).to_be_visible(timeout=30000)
        check(cp.locator("text=Only sample tests run here").count() == 1, "sample run result rendered")
        shot(cp, "04_candidate_dsa_after_run")
        cp.get_by_role("button", name=re.compile("Submit round")).click()
        cp.get_by_role("button", name=re.compile("Yes, submit")).click()
        cp.wait_for_timeout(2500)
        shot(cp, "05_candidate_explanation_check")
        # Post-code explanation check: answer each grounded question, then proceed.
        expect(cp.get_by_text("Post-Submission Cross-Examination")).to_be_visible(timeout=30000)
        modal_q = cp.locator("h3, p.font-bold, .font-bold").filter(has_text="?").first.inner_text()
        print("explanation question 1:", modal_q)
        check("'sys'" not in modal_q, "explanation question is about the candidate's logic, not an import")
        check(cp.get_by_text("Don't run anything").count() == 0, "next round not opened (clock not started) during explanation check")
        expl = ["A dict from value to index gives O(1) complement lookups, so one pass is enough.",
                "I check the complement before inserting, so an element never pairs with itself.",
                "On empty or single-element input the loop never finds a pair and prints nothing."]
        for text in expl:
            box = cp.locator("textarea[placeholder^='Explain']")
            try:
                box.wait_for(state="visible", timeout=60000)
            except Exception:
                break
            box.fill(text)
            cp.get_by_role("button", name=re.compile("Next Question|Submit All Explanations")).click()
            cp.wait_for_timeout(800)
        cp.get_by_role("button", name=re.compile("Proceed to Next Round")).click(timeout=60000)

        # ---------------- round 2: comprehension
        expect(cp.get_by_text(re.compile("Don't run anything"))).to_be_visible(timeout=20000)
        shot(cp, "06_candidate_comprehension")
        boxes = cp.locator("textarea[placeholder]")
        answers = ["It retries fn with exponential backoff capped at cap, and re-raises after the last attempt.",
                   "None 3 3", "L11: attempt == attempts is never true because range stops at attempts - 1, so after the last failure it returns None instead of raising.",
                   "Add jitter; sleeps are synchronized across clients so retries stampede.", "0.1 + 0.2 + 0.4 + 0.8 = 1.5 seconds"]
        for i, text in enumerate(answers):
            area = cp.locator("textarea[placeholder]").first
            if not area.count():
                break
            area.fill(text)
            cp.get_by_role("button", name=re.compile("Submit answer|Answer follow-up")).first.click()
            cp.wait_for_timeout(2500)
        page_text = cp.inner_text("body")
        check(not re.search(r"\b(correct|incorrect|score|\d+%)\b", page_text, re.I), "no verdicts or scores on comprehension screen")
        shot(cp, "07_candidate_comprehension_answered")
        cp.get_by_role("button", name=re.compile("Submit round")).click()
        cp.get_by_role("button", name=re.compile("Yes, submit")).click()

        # ---------------- round 3: interview
        replies = ["I used a hash map from value to index, one pass, O(n) time and O(n) space.",
                   "I check for the complement before inserting, so a value pairing with itself only works if it appears twice.",
                   "I'd add tests for negatives, duplicates and no-solution input, and measure on 10^5 elements."]
        try:
            expect(cp.get_by_text(re.compile("The interviewer may ask"))).to_be_visible(timeout=60000)
        except AssertionError:
            shot(cp, "08_candidate_interview_FAILED")
            print("console errors:", console_errors[-8:])
            raise
        for text in replies:
            if not cp.get_by_placeholder("Your answer").count():
                break
            cp.get_by_placeholder("Your answer").fill(text)
            cp.get_by_role("button", name=re.compile("^Send")).click()
            cp.wait_for_timeout(500)
            cp.wait_for_function("!document.body.innerText.includes('Sending...')", timeout=60000)
        shot(cp, "08_candidate_interview")
        qs = cp.locator(".rounded-tl-sm").all_inner_texts()
        print("interview questions:", *qs, sep="\n  ")
        check(len(qs) == 3 and len(set(qs)) == 3, "3 distinct interviewer questions")
        cp.get_by_role("button", name=re.compile("Finish assessment")).click()
        cp.get_by_role("button", name=re.compile("Yes, submit")).click()
        expect(cp.get_by_role("heading", name="Submitted")).to_be_visible(timeout=60000)
        body = cp.inner_text("body")
        check("%" not in body and "score" not in body.lower().replace("results aren't shown", ""), "completion screen shows no score")
        shot(cp, "09_candidate_completed")

        # ---------------- recruiter leaderboard
        rp.reload()
        rp.get_by_role("button", name=re.compile("leaderboard", re.I)).first.click()
        rp.wait_for_timeout(500)
        sel = rp.locator("select").first
        if sel.count():
            try:
                sel.select_option(pipe["id"])
            except Exception:
                pass
        rp.wait_for_timeout(1500)
        shot(rp, "10_recruiter_leaderboard")
        lb = httpx.get(f"{API}/enterprise/pipelines/{pipe['id']}/leaderboard", headers={"Authorization": f"Bearer {tok}"}).json()
        c = lb["candidates"][0]
        print("leaderboard:", {k: (v or {}).get("score") for k, v in c["round_results"].items()}, "composite", c["composite_score"], "rank", c["rank"])
        check(c["round_results"]["0"]["score"] == 100.0, "DSA round scored 100 from hidden tests")
        check(c["round_results"]["1"]["score"] is not None, "comprehension round scored")
        check(c["rank"] == 1 and c["access_token"] == "", "ranked #1, no token exposed")
        print("interview round:", c["round_results"]["2"]["status"], c["round_results"]["2"].get("score"),
              (c["round_results"]["2"].get("details") or {}).get("summary"))
        browser.close()

    errs = [e for e in console_errors if "favicon" not in e[1]]
    check(not errs, f"no console errors ({errs[:3]})")
    print(f"\n{len(findings)} findings. Screenshots in {OUT}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
