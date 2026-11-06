import uuid

import pytest

from backend.app.notifications.templates import assessment_invite


def test_invite_template_escapes_and_links():
    subject, text, html = assessment_invite(
        "<script>x</script>", "a@b.com", "Drive <b>1</b>", "SDE", "Acme & Co",
        [{"name": "Coding", "round_type": "oa_dsa", "time_limit_minutes": 30}], "http://localhost:5173/assess/take/abc", "13 Nov 2026")
    assert "<script>" not in html and "&lt;script&gt;" in html and "Acme &amp; Co" in html
    assert 'href="http://localhost:5173/assess/take/abc"' in html and "http://localhost:5173/assess/take/abc" in text
    assert "Acme & Co" in subject and "13 Nov 2026" in html


@pytest.mark.asyncio
async def test_invite_endpoint_reports_email_status_without_sending_in_tests(client):
    email = f"rec_{uuid.uuid4().hex[:6]}@acme.dev"
    await client.post("/api/v1/auth/register-recruiter", json={"organisation_name": "Acme", "email": email, "password": "Password123!"})
    tok = (await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    p = (await client.post("/api/v1/enterprise/pipelines", headers=h, json={"title": "Drive", "job_description": "Backend work in Python"})).json()
    r = (await client.post(f"/api/v1/enterprise/pipelines/{p['id']}/invite", headers=h,
                           json={"candidate_name": "Asha", "candidate_email": "asha@example.com"})).json()
    assert r["email_sent"] is False and r["email_detail"] == "disabled in tests"
