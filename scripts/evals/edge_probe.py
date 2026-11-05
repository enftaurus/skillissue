#!/usr/bin/env python3
"""
Edge-case probe against a running stack. Flags 5xx responses and suspicious 2xx (things that
should have been rejected). Uses two throwaway accounts to test cross-user isolation.

    backend/venv/bin/python scripts/evals/edge_probe.py
"""
import asyncio
import json
import os
import uuid

import httpx
import websockets

API = os.environ.get("SKILLISSUE_API", "http://localhost:8000/api/v1")
WS = API.replace("http", "ws", 1)
findings = []


def check(name, r, expect_ok=False, ok_codes=None):
    code = r.status_code
    bad = code >= 500 or (not expect_ok and code < 300 and ok_codes is None) or (ok_codes and code not in ok_codes)
    tag = "BUG " if bad else "ok  "
    if bad:
        findings.append((name, code, r.text[:200]))
    print(f"{tag}{code} {name}" + (f"  -> {r.text[:160]}" if bad else ""))


async def account(c):
    email = f"probe_{uuid.uuid4().hex[:8]}@example.com"
    await c.post("/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await c.post("/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}, tok


async def main():
    async with httpx.AsyncClient(base_url=API, timeout=120) as c:
        a, a_tok = await account(c)
        b, _ = await account(c)

        # --- auth
        check("register duplicate", await c.post("/auth/register", json={"email": "x" * 300 + "@e.com", "password": "Password123!"}))
        check("login wrong password", await c.post("/auth/login", json={"email": "nobody@example.com", "password": "x"}))
        check("refresh token used as access", await c.get("/interviews", headers={"Authorization": "Bearer abc.def.ghi"}))

        # --- interviews (mock/real provider of the throwaway account: creation may 400 without BYOC)
        r = await c.post("/interviews/domain", headers=a, json={"category": "technical", "domain_skills": ["Python"]})
        print(f"info {r.status_code} create interview for probe account (needs a verified provider outside tests)")
        check("create interview: unknown category", await c.post("/interviews/domain", headers=a, json={"category": "astrology", "domain_skills": ["x"]}))
        check("create interview: empty skills", await c.post("/interviews/domain", headers=a, json={"category": "technical", "domain_skills": []}))
        check("create interview: 500 skills", await c.post("/interviews/domain", headers=a, json={"category": "technical", "domain_skills": ["s"] * 500}))
        check("create interview: duration 0", await c.post("/interviews/domain", headers=a, json={"category": "technical", "domain_skills": ["x"], "target_duration_minutes": 0}))
        check("create interview: duration 10000", await c.post("/interviews/domain", headers=a, json={"category": "technical", "domain_skills": ["x"], "target_duration_minutes": 10000}))
        fake = str(uuid.uuid4())
        check("message to nonexistent interview", await c.post(f"/interviews/{fake}/message", headers=a, json={"content": "hi"}))
        check("message: empty content", await c.post(f"/interviews/{fake}/message", headers=a, json={"content": ""}))
        check("message: 200k content", await c.post(f"/interviews/{fake}/message", headers=a, json={"content": "a" * 200_000}))
        check("hint level 9", await c.post(f"/interviews/{fake}/hint", headers=a, json={"level": 9}))
        check("code: bad language", await c.post(f"/interviews/{fake}/code", headers=a, json={"language": "brainfuck", "code": "+"}))
        check("state of nonexistent", await c.get(f"/interviews/{fake}/state", headers=a))

        # --- evaluations
        check("self-eval for foreign interview", await c.post("/evaluations/self", headers=a, json={"interview_id": fake, "dimension_scores": {"x": 3}}))
        check("self-eval score out of range", await c.post("/evaluations/self", headers=a, json={"interview_id": fake, "dimension_scores": {"x": 99}}))
        check("generate eval for foreign", await c.post(f"/evaluations/{fake}/generate", headers=a))

        # --- comprehension
        check("comprehension: unknown item", await c.post("/comprehension/sessions", headers=a, json={"item_id": "nope"}))
        s = (await c.post("/comprehension/sessions", headers=a, json={"item_id": "retry-helper"})).json()
        sid = s["id"]
        check("comprehension: other user's session", await c.get(f"/comprehension/sessions/{sid}", headers=b))
        check("comprehension: other user answers", await c.post(f"/comprehension/sessions/{sid}/answer", headers=b, json={"question_id": "q1", "answer": "x"}))
        check("comprehension: other user finishes", await c.post(f"/comprehension/sessions/{sid}/finish", headers=b))
        check("comprehension: unknown question", await c.post(f"/comprehension/sessions/{sid}/answer", headers=a, json={"question_id": "q99", "answer": "x"}))
        check("comprehension: whitespace answer", await c.post(f"/comprehension/sessions/{sid}/answer", headers=a, json={"question_id": "q1", "answer": "   \n "}))
        check("comprehension: 9k answer", await c.post(f"/comprehension/sessions/{sid}/answer", headers=a, json={"question_id": "q1", "answer": "x" * 9000}))
        check("comprehension: unicode/RTL/NUL answer", await c.post(f"/comprehension/sessions/{sid}/answer", headers=a,
                                                                      json={"question_id": "q1", "answer": "None 3 3 ‮\u0000 😀"}), ok_codes=[200])
        dup = await asyncio.gather(*[c.post(f"/comprehension/sessions/{sid}/answer", headers=a, json={"question_id": "q4", "answer": "1.5 seconds"}) for _ in range(4)])
        codes = sorted(r.status_code for r in dup)
        print(f"{'BUG ' if codes.count(200) > 1 else 'ok  '}{codes} comprehension: 4 concurrent answers to one question")
        if codes.count(200) > 1:
            findings.append(("comprehension concurrent double-answer", codes, ""))
        fin = (await c.post(f"/comprehension/sessions/{sid}/finish", headers=a)).json()
        q4 = fin["answers"].get("q4", {}).get("score")
        print(f"info finish score={fin['score']} q4={q4}")

        # --- projects
        check("projects: unknown project run", await c.post("/projects/nope/run-tests", headers=a, json={"files": {}}))
        check("projects: path traversal key", await c.post("/projects/async-job-queue/run-tests", headers=a,
                                                           json={"files": {"../../../tmp/pwn.py": "x", "src/dispatcher.py": "pass"}}), ok_codes=[200])
        check("projects: 5 MB file", await c.post("/projects/async-job-queue/run-tests", headers=a, json={"files": {"src/dispatcher.py": "#" * 5_000_000}}))
        check("projects: copilot huge message", await c.post("/projects/async-job-queue/copilot", headers=a,
                                                             json={"files": {}, "message": "x" * 100_000}))

        # --- audio
        check("tts: 13k text", await c.post("/audio/tts", headers=a, json={"text": "a" * 13000}))
        check("tts: unknown voice id", await c.post("/audio/tts", headers=a, json={"text": "hello", "voice": "../../etc"}), ok_codes=[200])
        check("stt: empty file", await c.post("/audio/stt", headers=a, files={"audio": ("a.webm", b"", "audio/webm")}), ok_codes=[200])

        # --- interviews with a provider-backed account (set SKILLISSUE_EVAL_EMAIL / _PASSWORD)
        if os.environ.get("SKILLISSUE_EVAL_EMAIL"):
            tok = (await c.post("/auth/login", json={"email": os.environ["SKILLISSUE_EVAL_EMAIL"],
                                                     "password": os.environ["SKILLISSUE_EVAL_PASSWORD"]})).json()["access_token"]
            m = {"Authorization": f"Bearer {tok}"}
            iv = (await c.post("/interviews/domain", headers=m, json={"category": "technical", "domain_skills": ["Python"]})).json()
            iid = iv["id"]
            check("other user reads interview", await c.get(f"/interviews/{iid}", headers=b))
            check("other user posts message", await c.post(f"/interviews/{iid}/message", headers=b, json={"content": "hi"}))
            check("other user ends interview", await c.post(f"/interviews/{iid}/end", headers=b))
            check("other user voice-less state", await c.get(f"/interviews/{iid}/state", headers=b))
            check("message: 200k content", await c.post(f"/interviews/{iid}/message", headers=m, json={"content": "a" * 200_000}))
            check("message: NUL/RTL/emoji", await c.post(f"/interviews/{iid}/message", headers=m,
                                                         json={"content": "I used \u0000 Redis \u202e😀 for caching sessions.", "client_turn_id": "t-unicode"}), ok_codes=[200])
            turn = str(uuid.uuid4())
            dup = await asyncio.gather(*[c.post(f"/interviews/{iid}/message", headers=m,
                                                json={"content": "We used Postgres row locks.", "client_turn_id": turn}) for _ in range(3)])
            codes = [r.status_code for r in dup]
            ids = {r.json().get("id") for r in dup if r.status_code == 200}
            detail = (await c.get(f"/interviews/{iid}", headers=m)).json()
            users = [x for x in detail["messages"] if x["role"] == "user" and x["content"] == "We used Postgres row locks."]
            bad = len(users) != 1 or any(code >= 500 for code in codes)
            print(f"{'BUG ' if bad else 'ok  '}{codes} concurrent double-submit same client_turn_id -> {len(users)} stored, {len(ids)} distinct replies")
            if bad:
                findings.append(("interview concurrent double-submit", codes, f"{len(users)} stored"))
            await c.post(f"/interviews/{iid}/end", headers=m)
            check("message after end", await c.post(f"/interviews/{iid}/message", headers=m, json={"content": "hello?"}))
            check("hint after end", await c.post(f"/interviews/{iid}/hint", headers=m, json={"level": 1}))

        # --- features added 2026-11-06
        check("dispute: foreign evaluation", await c.post(f"/evaluations/{fake}/disputes", headers=a,
                                                          json={"dimension_id": "technical_depth", "quote": "x" * 20, "argument": "y" * 20}))
        check("dispute: short quote", await c.post(f"/evaluations/{fake}/disputes", headers=a,
                                                   json={"dimension_id": "technical_depth", "quote": "x", "argument": "y" * 20}))
        check("replay diff: unknown retest", await c.get(f"/evaluations/retests/{fake}/diff", headers=a))
        check("delivery: foreign interview", await c.get(f"/interviews/{fake}/delivery", headers=a))
        check("timeline: unknown project", await c.get("/projects/nope/timeline", headers=a))
        check("self-awareness empty", await c.get("/analytics/self-awareness", headers=a), ok_codes=[200])
        check("voice status", await c.get("/voice/status"), ok_codes=[200])
        if os.environ.get("SKILLISSUE_EVAL_EMAIL"):
            tok2 = (await c.post("/auth/login", json={"email": os.environ["SKILLISSUE_EVAL_EMAIL"],
                                                      "password": os.environ["SKILLISSUE_EVAL_PASSWORD"]})).json()["access_token"]
            m2 = {"Authorization": f"Bearer {tok2}"}
            for _ in range(10):
                rr = await c.post("/interviews/domain", headers=m2, json={"category": "technical", "domain_skills": ["Python"]})
                if rr.status_code != 429:
                    break
                await asyncio.sleep(10)
            iid2 = rr.json()["id"]
            check("delivery: absurd numbers clamped", await c.post(f"/interviews/{iid2}/message", headers=m2, json={
                "content": "We used Redis.", "client_turn_id": str(uuid.uuid4()),
                "delivery": [{"words": 10**12, "duration_s": -1, "fillers": {"um": 10**9, "x" * 100: 5}}]}), ok_codes=[200])
            d = (await c.get(f"/interviews/{iid2}/delivery", headers=m2)).json()["summary"]
            ok = d is None or (d.get("top_fillers") and d["top_fillers"][0][1] <= 500)
            print(f"{'ok  ' if ok else 'BUG '}delivery summary clamped -> {d}")
            if not ok:
                findings.append(("delivery clamp", d, ""))
            check("delivery: other user reads", await c.get(f"/interviews/{iid2}/delivery", headers=b))
            check("delivery: 11 parts rejected", await c.post(f"/interviews/{iid2}/message", headers=m2, json={
                "content": "More.", "delivery": [{"words": 1}] * 11}))

        # --- executor endpoint requires its secret
        async with httpx.AsyncClient(timeout=10) as ex:
            try:
                r = await ex.post("http://127.0.0.1:8001/execute-project", json={"repository_files": {}, "editable_files": [], "candidate_files": {}})
                check("executor /execute-project without secret", r)
            except httpx.ConnectError:
                print("info executor not reachable")

        # --- coding
        check("coding: unknown problem", await c.post("/coding/run", headers=a, json={"problem_id": "nope-123", "language": "python", "code": "print(1)"}))

    # --- voice websocket
    async def ws_probe(name, first, expect_code):
        try:
            async with websockets.connect(f"{WS}/voice/ws/{uuid.uuid4()}") as ws:
                if first is not None:
                    await ws.send(first)
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
                ok = msg.get("code") == expect_code
                print(f"{'ok  ' if ok else 'BUG '}{msg.get('code')} voice ws: {name}")
                if not ok:
                    findings.append((f"voice ws {name}", msg, ""))
        except Exception as e:
            print(f"BUG voice ws {name}: {type(e).__name__} {e}")
            findings.append((f"voice ws {name}", type(e).__name__, str(e)))

    await ws_probe("garbage first frame", "not json", "AUTH_REQUIRED")
    await ws_probe("valid token, foreign interview", json.dumps({"type": "auth", "token": a_tok}), "NOT_FOUND")
    await ws_probe("wrong message type", json.dumps({"type": "audio", "data": "AAAA"}), "AUTH_REQUIRED")

    print("\nFINDINGS:", len(findings))
    for f in findings:
        print(" -", f)


asyncio.run(main())
