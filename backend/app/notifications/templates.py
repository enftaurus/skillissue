"""Email templates. Every interpolated value is HTML-escaped (names and titles are user input)."""
from html import escape
from typing import Any, Dict, List, Optional, Tuple

_ROUND_LABEL = {"oa_dsa": "Coding assessment", "code_comprehension": "Code comprehension",
                "ai_project": "Project in a real repository", "tough_interview": "Technical interview"}


def assessment_invite(candidate_name: str, candidate_email: str, pipeline_title: str, target_role: str,
                      company: Optional[str], rounds: List[Dict[str, Any]], link: str, expires: Optional[str]) -> Tuple[str, str, str]:
    """Returns (subject, text, html)."""
    org = company or "The hiring team"
    subject = f"{org} invited you to the {pipeline_title} assessment"
    total = sum(int(r.get("time_limit_minutes") or 0) for r in rounds)
    n, t, r_, e = escape(candidate_name or "there"), escape(pipeline_title), escape(target_role), escape(org)
    em, url = escape(candidate_email), escape(link, quote=True)

    rows = "".join(
        f'''<tr>
          <td style="padding:10px 0;border-bottom:1px solid #F4F4F5;width:28px;vertical-align:top;">
            <div style="width:22px;height:22px;border-radius:11px;background:#F7FEE7;border:1px solid #D9F99D;color:#3F6212;font:600 11px/22px 'Courier New',monospace;text-align:center;">{i + 1}</div>
          </td>
          <td style="padding:10px 0 10px 10px;border-bottom:1px solid #F4F4F5;font:600 14px/20px Arial,Helvetica,sans-serif;color:#09090B;">
            {escape(r.get("name") or _ROUND_LABEL.get(r.get("round_type"), "Round"))}
            {"" if (r.get("name") or "").strip().lower() == _ROUND_LABEL.get(r.get("round_type"), "").lower() else '<div style="font:400 12px/18px Arial,Helvetica,sans-serif;color:#71717A;">' + escape(_ROUND_LABEL.get(r.get("round_type"), "")) + '</div>'}
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #F4F4F5;text-align:right;font:400 12px/20px 'Courier New',monospace;color:#71717A;white-space:nowrap;">{int(r.get("time_limit_minutes") or 0)} min</td>
        </tr>''' for i, r in enumerate(rounds))

    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><title>{escape(subject)}</title></head>
<body style="margin:0;padding:0;background:#F4F4F5;">
<div style="display:none;max-height:0;overflow:hidden;">{e} invited you to a {total}-minute assessment for {r_}.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#F4F4F5;padding:32px 12px;">
<tr><td align="center">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;">
    <tr><td style="padding:0 4px 16px;font:700 15px/20px Arial,Helvetica,sans-serif;color:#09090B;">
      <span style="display:inline-block;width:10px;height:10px;border-radius:3px;background:#84CC16;margin-right:8px;"></span>Skill Issue
    </td></tr>
    <tr><td style="background:#FFFFFF;border:1px solid #E4E4E7;border-radius:16px;overflow:hidden;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        <tr><td style="background:#09090B;padding:28px 28px 24px;">
          <div style="font:600 11px/16px 'Courier New',monospace;letter-spacing:1.5px;color:#A3E635;text-transform:uppercase;">Assessment invitation</div>
          <div style="font:700 24px/30px Arial,Helvetica,sans-serif;color:#FFFFFF;margin-top:8px;">{t}</div>
          <div style="font:400 14px/20px Arial,Helvetica,sans-serif;color:#A1A1AA;margin-top:6px;">{e} &middot; {r_}</div>
        </td></tr>
        <tr><td style="padding:28px;">
          <p style="margin:0 0 14px;font:400 15px/24px Arial,Helvetica,sans-serif;color:#18181B;">Hi {n},</p>
          <p style="margin:0 0 20px;font:400 15px/24px Arial,Helvetica,sans-serif;color:#3F3F46;">
            {e} has invited you to take a timed online assessment for the <strong style="color:#09090B;">{r_}</strong> role.
            It has {len(rounds)} round{"s" if len(rounds) != 1 else ""}, about {total} minutes in total. Each round's clock starts only when you open it.
          </p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">{rows}</table>
          <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 8px;"><tr>
            <td style="border-radius:12px;background:#09090B;">
              <a href="{url}" target="_blank" style="display:inline-block;padding:14px 28px;font:700 15px/20px Arial,Helvetica,sans-serif;color:#FFFFFF;text-decoration:none;border-radius:12px;">
                Start your assessment <span style="color:#A3E635;">&rarr;</span></a>
            </td></tr></table>
          <p style="margin:0 0 24px;text-align:center;font:400 12px/18px Arial,Helvetica,sans-serif;color:#A1A1AA;">
            Or paste this link into your browser:<br><a href="{url}" style="color:#4D7C0F;word-break:break-all;">{escape(link)}</a></p>
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#FAFAFA;border:1px solid #E4E4E7;border-radius:12px;">
            <tr><td style="padding:16px 18px;font:400 13px/21px Arial,Helvetica,sans-serif;color:#3F3F46;">
              <strong style="color:#09090B;">Before you start</strong><br>
              &bull; Sign in, or create a free account, with <strong style="color:#09090B;">{em}</strong>. The invitation is tied to this address.<br>
              &bull; Use a laptop with a stable connection; Chrome works best for the voice interview.<br>
              &bull; Rounds go in order and can't be reopened once submitted.<br>
              &bull; Your results go to {e}. You won't see scores on the platform.
              {("<br>&bull; This invitation expires on <strong>" + escape(expires) + "</strong>.") if expires else ""}
            </td></tr></table>
        </td></tr>
      </table>
    </td></tr>
    <tr><td style="padding:18px 8px;text-align:center;font:400 12px/18px Arial,Helvetica,sans-serif;color:#A1A1AA;">
      You received this because {e} invited {em} to an assessment on Skill Issue.<br>
      If you weren't expecting it, you can ignore this email.
    </td></tr>
  </table>
</td></tr></table>
</body></html>'''

    lines = [f"Hi {candidate_name or 'there'},", "",
             f"{org} invited you to the {pipeline_title} assessment for the {target_role} role "
             f"({len(rounds)} rounds, about {total} minutes; each round's clock starts when you open it).", ""]
    lines += [f"  {i + 1}. {r.get('name') or _ROUND_LABEL.get(r.get('round_type'), 'Round')} ({int(r.get('time_limit_minutes') or 0)} min)"
              for i, r in enumerate(rounds)]
    lines += ["", f"Start here: {link}", "",
              f"Sign in or create an account with {candidate_email}; the invitation is tied to this address.",
              "Rounds go in order. Your results go to the hiring team; you won't see scores on the platform."]
    if expires:
        lines.append(f"This invitation expires on {expires}.")
    return subject, "\n".join(lines), html
