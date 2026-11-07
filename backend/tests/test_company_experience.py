import uuid

import pytest

from backend.app.interviews.prompts import build_interviewer_system_prompt


async def _login(client):
    email = f"ce_{uuid.uuid4().hex[:8]}@example.com"
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_prompt_carries_level_company_and_jd_scope():
    p = build_interviewer_system_prompt(category="technical", target_role="SDE-1", difficulty="intermediate",
                                        jd_role="SDE-1", jd_skills=["Java"], jd_requirements=["Build payment APIs"],
                                        company_name="Zerodha", experience_level="fresher")
    assert "CANDIDATE LEVEL: FRESHER" in p and "JOB DESCRIPTION SCOPE" in p and "Zerodha" in p
    assert "Uber" not in build_interviewer_system_prompt(category="technical", target_role="x", difficulty="x", company_name="Zerodha")


@pytest.mark.asyncio
async def test_domain_interview_stores_company_and_experience(client):
    h = await _login(client)
    r = (await client.post("/api/v1/interviews/domain", headers=h, json={
        "category": "technical", "domain_skills": ["Java"], "company_name": "Zerodha", "experience_level": "fresher"})).json()
    assert r["company_name"] == "Zerodha" and r["experience_level"] == "fresher" and r["title"].startswith("Zerodha · ")
    r = (await client.post("/api/v1/interviews/domain", headers=h, json={
        "category": "technical", "domain_skills": ["Go"], "company_name": "uber", "experience_level": "mid"})).json()
    assert r["company_name"] == "Uber"  # registry spelling
    bad = await client.post("/api/v1/interviews/domain", headers=h, json={"category": "technical", "domain_skills": ["Go"], "experience_level": "wizard"})
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_jd_interview_uses_jd_company_with_overrides(client):
    h = await _login(client)
    jd = (await client.post("/api/v1/job-descriptions", headers=h, json={
        "title": "SDE-1", "company": "Razorpay", "raw_text": "We are hiring SDE-1 engineers to build payment APIs in Java and MySQL."})).json()
    assert jd["company"] == "Razorpay" and "extracted_experience" in jd
    r = (await client.post("/api/v1/interviews/jd", headers=h, json={"category": "technical", "jd_id": jd["id"],
                                                                     "experience_level": "junior"})).json()
    assert r["company_name"] == "Razorpay" and r["experience_level"] == "junior" and "@ Razorpay" in r["title"]


@pytest.mark.asyncio
async def test_overlong_titles_and_roles_do_not_500(client):
    """E14: titles built from JD role + company (or long skills) overflowed interviews.title String(255) /
    target_role String(150) and 500'd as a Postgres DataError."""
    h = await _login(client)
    jd = (await client.post("/api/v1/job-descriptions", headers=h, json={
        "title": "R" * 200, "company": "C" * 200,
        "raw_text": "We are hiring engineers to build payment APIs in Java and MySQL."})).json()
    # Pin the extracted role to the max the JD schema allows (the mock extractor may return something shorter).
    upd = await client.put(f"/api/v1/job-descriptions/{jd['id']}", headers=h, json={"extracted_role": "E" * 200})
    assert upd.status_code == 200, upd.text
    r = await client.post("/api/v1/interviews/jd", headers=h, json={"category": "technical", "jd_id": jd["id"]})
    assert r.status_code == 201, r.text
    assert len(r.json()["title"]) <= 255 and len(r.json()["target_role"]) <= 150
    r = await client.post("/api/v1/interviews/domain", headers=h, json={
        "category": "technical", "domain_skills": ["S" * 150] * 3, "target_role": "T" * 150})
    assert r.status_code == 201, r.text
    assert len(r.json()["title"]) <= 255
    r = await client.post("/api/v1/interviews/domain", headers=h, json={
        "category": "technical", "domain_skills": ["Go"], "target_role": "T" * 151})
    assert r.status_code == 422
    r = await client.post("/api/v1/interviews/jd", headers=h, json={"category": "technical", "jd_id": jd["id"],
                                                                    "difficulty": "x" * 21})
    assert r.status_code == 422


def test_company_calibration_matches_whole_words_only():
    """E15: 'meta' in 'Metabase' (or 'uber' in 'Tuberlabs') pulled in Meta/Uber calibration."""
    p = build_interviewer_system_prompt(category="technical", target_role="x", difficulty="x", company_name="Metabase")
    assert "COMPANY CALIBRATION: META" not in p and "Metabase" in p
    p = build_interviewer_system_prompt(category="technical", target_role="x", difficulty="x", company_name="Tuberlabs")
    assert "UBER" not in p and "Tuberlabs" in p
    p = build_interviewer_system_prompt(category="technical", target_role="x", difficulty="x", company_name="Meta Platforms")
    assert "COMPANY CALIBRATION: META" in p
