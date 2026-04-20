from __future__ import annotations

import json
from typing import Any

from clipper.storage import Storage


def _json_response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps(body, ensure_ascii=False),
    }


def _html_response(status: int, html: str) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "text/html; charset=utf-8"},
        "body": html,
    }


def handle_http_event(storage: Storage, event: dict[str, Any]) -> dict[str, Any]:
    req = event.get("requestContext", {}).get("http", {}) or {}
    method = (req.get("method") or event.get("httpMethod") or "GET").upper()
    path = event.get("rawPath") or event.get("path") or "/"
    qs = event.get("queryStringParameters") or {}

    if method != "GET":
        return _json_response(405, {"error": "method_not_allowed"})

    if path in ("/", ""):
        dash = storage.read_json("state/dashboard_snapshot.json") or {}
        return _html_response(200, render_dashboard_html(dash))

    if path == "/api/dashboard":
        dash = storage.read_json("state/dashboard_snapshot.json") or {}
        return _json_response(200, dash)

    if path == "/api/items":
        dash = storage.read_json("state/dashboard_snapshot.json") or {}
        items = list(dash.get("recent_items") or [])
        decision = qs.get("decision") if isinstance(qs, dict) else None
        category = qs.get("category") if isinstance(qs, dict) else None
        if decision:
            items = [x for x in items if x.get("decision") == decision]
        if category:
            items = [x for x in items if x.get("category") == category]
        return _json_response(200, {"items": items})

    return _json_response(404, {"error": "not_found"})


def render_dashboard_html(dash: dict[str, Any]) -> str:
    summary = dash.get("summary") or {}
    jobs = dash.get("jobs") or {}
    sends = dash.get("recent_sends") or []
    items = dash.get("recent_items") or []
    fails = dash.get("recent_failures") or []
    gen = dash.get("generated_at") or "-"

    def job_block(name: str) -> str:
        j = jobs.get(name) or {}
        return f"""
        <section class="card">
          <h3>{name}</h3>
          <table>
            <tr><td>last_run_at</td><td>{esc(j.get('last_run_at'))}</td></tr>
            <tr><td>status</td><td>{esc(j.get('status'))}</td></tr>
            <tr><td>fetched</td><td>{esc(j.get('fetched_count'))}</td></tr>
            <tr><td>filtered</td><td>{esc(j.get('filtered_count'))}</td></tr>
            <tr><td>sent</td><td>{esc(j.get('sent_count'))}</td></tr>
            <tr><td>errors</td><td>{esc(j.get('error_count'))}</td></tr>
            <tr><td>duration_ms</td><td>{esc(j.get('duration_ms'))}</td></tr>
          </table>
        </section>
        """

    rows_sends = "\n".join(_row_send(r) for r in sends[:80])
    rows_items = "\n".join(_row_item(r) for r in items[:120])
    rows_fail = "\n".join(_row_fail(r) for r in fails[:80])

    jl = summary.get("job_last") or {}
    job_last_html = "".join(
        f"<div><b>{k}</b>: success {esc((v or {}).get('success_at'))} / fail {esc((v or {}).get('fail_at'))}</div>"
        for k, v in jl.items()
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>클리핑 운영 대시보드</title>
<style>
body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; color: #111; }}
header {{ margin-bottom: 16px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 12px; background: #fafafa; }}
table {{ width: 100%; border-collapse: collapse; }}
td {{ padding: 4px 6px; vertical-align: top; }}
td:first-child {{ color: #555; width: 140px; }}
section {{ margin-top: 22px; }}
table.data td, table.data th {{ border-bottom: 1px solid #eee; font-size: 13px; }}
th {{ text-align: left; }}
.mono {{ white-space: pre-wrap; word-break: break-all; }}
</style>
</head>
<body>
<header>
  <h1>대외정책 뉴스 클리핑 — 읽기 전용</h1>
  <p>스냅샷 생성: <span class="mono">{esc(gen)}</span></p>
  <p>최근 24h 발송: <b>{esc(summary.get('sent_24h'))}</b> · 실패: <b>{esc(summary.get('failed_24h'))}</b></p>
  <p>jobType 마지막 성공/실패 시각</p>
  <div class="mono">{job_last_html}</div>
</header>
<div class="grid">
  {job_block('x')}
  {job_block('youtube')}
  {job_block('news')}
  {job_block('gov')}
</div>

<section>
  <h2>최근 발송</h2>
  <table class="data">
    <tr><th>시각</th><th>분류</th><th>소스</th><th>제목/요약</th><th>링크</th><th>사유/키워드</th></tr>
    {rows_sends}
  </table>
</section>

<section>
  <h2>최근 크롤링/판정</h2>
  <table class="data">
    <tr><th>시각</th><th>분류</th><th>소스</th><th>제목</th><th>판정</th><th>사유</th><th>링크</th></tr>
    {rows_items}
  </table>
</section>

<section>
  <h2>최근 실패</h2>
  <table class="data">
    <tr><th>시각</th><th>job</th><th>소스</th><th>요약</th></tr>
    {rows_fail}
  </table>
</section>

<p style="margin-top:28px;color:#666;font-size:13px">
  JSON: <a href="/api/dashboard">/api/dashboard</a> ·
  <a href="/api/items">/api/items</a>
</p>
</body>
</html>
"""


def esc(v: Any) -> str:
    if v is None:
        return ""
    s = str(v)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _row_send(r: dict[str, Any]) -> str:
    title = r.get("summary_short") or r.get("title") or ""
    reason = r.get("reason") or ""
    mk = r.get("matched_keywords")
    if isinstance(mk, list):
        reason = reason or ",".join(str(x) for x in mk[:16])
    return f"<tr><td>{esc(r.get('at'))}</td><td>{esc(r.get('category'))}</td><td>{esc(r.get('source_name'))}</td><td class='mono'>{esc(title)}</td><td class='mono'><a href='{esc(r.get('link'))}' target='_blank' rel='noreferrer'>link</a></td><td class='mono'>{esc(reason)}</td></tr>"


def _row_item(r: dict[str, Any]) -> str:
    return f"<tr><td>{esc(r.get('at'))}</td><td>{esc(r.get('category'))}</td><td>{esc(r.get('source_name'))}</td><td class='mono'>{esc(r.get('title'))}</td><td>{esc(r.get('decision'))}</td><td class='mono'>{esc(r.get('reason'))}</td><td class='mono'><a href='{esc(r.get('link'))}' target='_blank' rel='noreferrer'>link</a></td></tr>"


def _row_fail(r: dict[str, Any]) -> str:
    return f"<tr><td>{esc(r.get('at'))}</td><td>{esc(r.get('jobType'))}</td><td>{esc(r.get('source_name'))}</td><td class='mono'>{esc(r.get('error_summary'))}</td></tr>"
