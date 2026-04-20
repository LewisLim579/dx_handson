from __future__ import annotations

import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from clipper.dashboard import (
    append_failure,
    append_item_row,
    append_send,
    build_empty_dashboard,
    recompute_summary_24h,
    update_job_card,
)
from clipper.dedupe import already_sent, register_sent
from clipper.http_util import fetch_url
from clipper.keywords import collect_keywords_for_source, keyword_filter, merge_normalize_maps
from clipper.llm import classify_x_relevance, summarize_youtube
from clipper.models import JobType, ParsedItem
from clipper.parsers import parse_for_profile
from clipper.state import load_json, merge_checkpoint_sources, prune_sent_entries, save_json, utc_now_iso
from clipper.storage import Storage, bootstrap_config_if_missing
from clipper.telegram_client import format_news_gov_line, format_x_line, format_youtube_line, send_telegram_message
from clipper.x_fetch import fetch_recent_tweets
from clipper.youtube_fetch import get_video_detail, resolve_channel_id_for_handle, search_cabinet_videos


def _bundle_config_dir() -> Path:
    root = os.environ.get("LAMBDA_TASK_ROOT") or str(Path(__file__).resolve().parents[1])
    return Path(root) / "config"


def _x_username_from_source_url(url: str) -> str | None:
    """`https://twitter.com/Jaemyung_Lee` / `x.com/...` 경로에서 사용자명 추출."""
    if not url or not isinstance(url, str):
        return None
    try:
        p = urlparse(url.strip())
        parts = [seg for seg in p.path.split("/") if seg]
        if not parts:
            return None
        return parts[0]
    except Exception:
        return None


def _youtube_handle_from_source_url(url: str) -> str | None:
    """`https://www.youtube.com/@ktv_kr` 형태에서 핸들(ktv_kr) 추출."""
    if not url or not isinstance(url, str):
        return None
    m = re.search(r"/@([^/?#]+)", url.strip())
    if m:
        return m.group(1).lstrip("@")
    return None


def ensure_bootstrap(storage: Storage) -> None:
    bootstrap_config_if_missing(storage, _bundle_config_dir())


def _output_prefix(subfolder: str) -> str:
    now = datetime.now(timezone.utc)
    return f"output/{subfolder}/{now.year:04d}/{now.month:02d}/{now.day:02d}"


def _artifact_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _write_run_artifact(storage: Storage, job: str, payload: dict[str, Any], ts: str) -> None:
    key = f"{_output_prefix('runs')}/{ts}-{job}.json"
    save_json(storage, key, payload)


def _write_items_or_failed_artifact(
    storage: Storage,
    subfolder: str,
    job: str,
    ts: str,
    payload: dict[str, Any],
) -> None:
    key = f"{_output_prefix(subfolder)}/{ts}-{job}.json"
    save_json(storage, key, payload)


def _load_prompt(storage: Storage, name: str) -> str:
    t = storage.read_text(f"config/prompts/{name}")
    return t or ""


def run_job(storage: Storage, job_type: JobType) -> dict[str, Any]:
    ensure_bootstrap(storage)
    t0 = time.monotonic()
    dash = load_json(storage, "state/dashboard_snapshot.json", None)
    if not isinstance(dash, dict):
        dash = build_empty_dashboard()
    sent_data = load_json(storage, "state/sent_items.json", {"entries": {}})
    entries = sent_data.get("entries") if isinstance(sent_data, dict) else {}
    if not isinstance(entries, dict):
        entries = {}
    entries = prune_sent_entries(entries, keep_days=30)
    checkpoint = load_json(storage, "state/checkpoints.json", {"sources": {}, "x": {}, "youtube": {}})
    health = load_json(storage, "state/source_health.json", {"sources": {}})
    kw = load_json(storage, "config/keywords.json", {})
    filters = load_json(storage, "config/filters.json", {})
    sources_doc = load_json(storage, "config/sources.json", {})
    src_list = sources_doc.get("sources") if isinstance(sources_doc, dict) else None
    if not isinstance(src_list, list):
        src_list = []

    alias_map = dict(filters.get("alias_map") or {})
    exclude_kw = list(filters.get("exclude_keywords") or [])
    strict_kw = list(filters.get("strict_keywords") or [])

    card = {
        "last_run_at": utc_now_iso(),
        "status": "running",
        "fetched_count": 0,
        "filtered_count": 0,
        "sent_count": 0,
        "error_count": 0,
        "duration_ms": 0,
    }
    success = True
    run_log: dict[str, Any] = {"job": job_type, "started_at": card["last_run_at"], "sources": []}

    err_msg: str | None = None
    artifact_ts = _artifact_timestamp()
    item_ledger: list[dict[str, Any]] = []
    fail_ledger: list[dict[str, Any]] = []
    try:
        if job_type in ("news", "gov"):
            subset = [s for s in src_list if s.get("category") == job_type]
            for src in subset:
                run_log["sources"].append(
                    _run_one_html_source(
                        storage,
                        src,
                        kw,
                        alias_map,
                        exclude_kw,
                        strict_kw,
                        entries,
                        checkpoint,
                        health,
                        dash,
                        item_ledger,
                        fail_ledger,
                    )
                )
        elif job_type == "x":
            run_log["x"] = _run_x_job(storage, src_list, entries, checkpoint, dash, item_ledger, fail_ledger)
        elif job_type == "youtube":
            run_log["youtube"] = _run_youtube_job(storage, src_list, entries, checkpoint, dash, item_ledger, fail_ledger)
        else:
            raise ValueError(f"unknown job {job_type}")

        # metrics from dash / run_log
        if job_type in ("news", "gov"):
            card["fetched_count"] = sum(s.get("parsed", 0) for s in run_log["sources"])
            card["filtered_count"] = sum(s.get("matched", 0) for s in run_log["sources"])
            card["sent_count"] = sum(s.get("sent", 0) for s in run_log["sources"])
            card["error_count"] = sum(1 for s in run_log["sources"] if s.get("error"))
        elif job_type == "x":
            x = run_log.get("x") or {}
            card["fetched_count"] = int(x.get("fetched", 0))
            card["filtered_count"] = int(x.get("ai_ok", 0))
            card["sent_count"] = int(x.get("sent", 0))
            card["error_count"] = int(x.get("errors", 0))
        elif job_type == "youtube":
            y = run_log.get("youtube") or {}
            card["fetched_count"] = int(y.get("candidates", 0))
            card["filtered_count"] = int(y.get("summarized", 0))
            card["sent_count"] = int(y.get("sent", 0))
            card["error_count"] = int(y.get("errors", 0))

        card["status"] = "ok"
    except Exception as e:
        success = False
        err_msg = str(e)
        card["status"] = "error"
        card["error_count"] = card.get("error_count", 0) + 1
        frow = {"at": utc_now_iso(), "jobType": job_type, "source_name": "*", "error_summary": str(e)[:500]}
        append_failure(dash, frow)
        fail_ledger.append(frow)
        run_log["fatal"] = str(e)
    finally:
        card["duration_ms"] = int((time.monotonic() - t0) * 1000)
        update_job_card(dash, job_type, card, success=success)
        recompute_summary_24h(dash)
        dash["generated_at"] = utc_now_iso()
        sent_data = {"entries": entries}
        save_json(storage, "state/sent_items.json", sent_data)
        save_json(storage, "state/checkpoints.json", checkpoint)
        save_json(storage, "state/source_health.json", health)
        save_json(storage, "state/dashboard_snapshot.json", dash)
        _write_run_artifact(storage, job_type, run_log, artifact_ts)
        _write_items_or_failed_artifact(
            storage,
            "items",
            job_type,
            artifact_ts,
            {
                "jobType": job_type,
                "artifact_ts": artifact_ts,
                "started_at": run_log.get("started_at") or card.get("last_run_at"),
                "items": item_ledger,
            },
        )
        _write_items_or_failed_artifact(
            storage,
            "failed",
            job_type,
            artifact_ts,
            {
                "jobType": job_type,
                "artifact_ts": artifact_ts,
                "failures": fail_ledger,
            },
        )

    if err_msg:
        return {"ok": False, "job": job_type, "error": err_msg, "card": card}
    return {"ok": True, "job": job_type, "card": card}


def _run_one_html_source(
    storage: Storage,
    src: dict[str, Any],
    kw: dict[str, Any],
    alias_map: dict[str, str],
    exclude_kw: list[str],
    strict_kw: list[str],
    entries: dict[str, Any],
    checkpoint: dict[str, Any],
    health: dict[str, Any],
    dash: dict[str, Any],
    item_ledger: list[dict[str, Any]],
    fail_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    sid = str(src.get("source_id"))
    profile = str(src.get("parser_profile") or "generic_list_fallback")
    url = str(src.get("url") or "")
    use_spec = bool(src.get("source_specific_keywords"))
    keywords, norm = collect_keywords_for_source(kw, sid, use_spec)
    norm = merge_normalize_maps(norm, alias_map)

    seen: set[str] = set((checkpoint.get("sources") or {}).get(sid, {}).get("seen_ids") or [])
    out: dict[str, Any] = {"source_id": sid, "parsed": 0, "matched": 0, "sent": 0, "error": None}

    try:
        code, html, _ = fetch_url(url)
        if code >= 400:
            raise RuntimeError(f"http_{code}")
        items = parse_for_profile(profile, html, url, sid)
        out["parsed"] = len(items)
        fresh: list[ParsedItem] = []
        for it in items:
            if it.external_id in seen:
                continue
            fresh.append(it)
        for it in items:
            seen.add(it.external_id)
        merge_checkpoint_sources(checkpoint, sid, {"seen_ids": list(seen)[-400:], "last_run_at": utc_now_iso()})

        for it in fresh:
            if already_sent(entries, it):
                row = {
                    "at": utc_now_iso(),
                    "category": src.get("category"),
                    "source_name": src.get("site_name"),
                    "title": it.title,
                    "decision": "skipped",
                    "reason": "duplicate_sent_index",
                    "link": it.link,
                }
                append_item_row(dash, row)
                item_ledger.append(row)
                continue
            text = f"{it.title} {it.summary_hint or ''}"
            fr = keyword_filter(text, keywords, norm, exclude_kw, strict_kw)
            if not fr.matched:
                row = {
                    "at": utc_now_iso(),
                    "category": src.get("category"),
                    "source_name": src.get("site_name"),
                    "title": it.title,
                    "decision": "skipped",
                    "reason": "keyword_filter",
                    "link": it.link,
                }
                append_item_row(dash, row)
                item_ledger.append(row)
                continue
            out["matched"] += 1
            line = format_news_gov_line(
                str(src.get("category")),
                str(src.get("site_name") or ""),
                str(src.get("menu_name") or ""),
                it.title,
                it.link,
                it.published_at,
            )
            ok, err = send_telegram_message(line)
            if not ok:
                out["error"] = err
                frow = {
                    "at": utc_now_iso(),
                    "jobType": src.get("category"),
                    "source_name": src.get("site_name"),
                    "error_summary": err or "telegram",
                }
                append_failure(dash, frow)
                fail_ledger.append(frow)
                irow = {
                    "at": utc_now_iso(),
                    "category": src.get("category"),
                    "source_name": src.get("site_name"),
                    "title": it.title,
                    "decision": "failed",
                    "reason": err or "telegram",
                    "link": it.link,
                }
                append_item_row(dash, irow)
                item_ledger.append(irow)
                continue
            register_sent(
                entries,
                it,
                {"source_id": sid, "category": src.get("category"), "matched_keywords": fr.matched_keywords},
            )
            out["sent"] += 1
            send_row = {
                "at": utc_now_iso(),
                "category": src.get("category"),
                "source_name": src.get("site_name"),
                "title": it.title,
                "summary_short": None,
                "link": it.link,
                "reason": ",".join(fr.matched_keywords[:12]),
                "matched_keywords": fr.matched_keywords,
            }
            append_send(dash, send_row)
            sent_row = {
                "at": send_row["at"],
                "category": src.get("category"),
                "source_name": src.get("site_name"),
                "title": it.title,
                "decision": "sent",
                "reason": ",".join(fr.matched_keywords[:12]),
                "link": it.link,
            }
            append_item_row(dash, sent_row)
            item_ledger.append(sent_row)

        hs = health.setdefault("sources", {}).setdefault(sid, {})
        hs["last_success_at"] = utc_now_iso()
        hs["last_error"] = None
        hs["fail_streak"] = 0
    except Exception as e:
        out["error"] = str(e)[:400]
        hs = health.setdefault("sources", {}).setdefault(sid, {})
        hs["last_error"] = str(e)[:400]
        hs["fail_streak"] = int(hs.get("fail_streak") or 0) + 1
        frow = {
            "at": utc_now_iso(),
            "jobType": src.get("category"),
            "source_name": src.get("site_name"),
            "error_summary": out["error"],
        }
        append_failure(dash, frow)
        fail_ledger.append(frow)
    return out


def _run_x_job(
    storage: Storage,
    src_list: list[dict[str, Any]],
    entries: dict[str, Any],
    checkpoint: dict[str, Any],
    dash: dict[str, Any],
    item_ledger: list[dict[str, Any]],
    fail_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    src = next((s for s in src_list if s.get("source_id") == "x_president"), None)
    if not src:
        raise RuntimeError("x_president missing in sources.json")
    prompt = _load_prompt(storage, "x_relevance_prompt.txt")
    username = _x_username_from_source_url(str(src.get("url") or "")) or "Jaemyung_Lee"
    since = (checkpoint.get("x") or {}).get("last_tweet_id")
    tweets, newest_id = fetch_recent_tweets(username, since_id=str(since) if since else None, max_results=10)
    stats = {"fetched": len(tweets), "ai_ok": 0, "sent": 0, "errors": 0}

    # oldest first for stable processing
    for tw in reversed(tweets):
        tid = tw.get("id")
        text = tw.get("text") or ""
        link = f"https://twitter.com/{username}/status/{tid}"
        fake = ParsedItem(external_id=str(tid), title=text[:120], link=link, published_at=tw.get("created_at"), raw={"x": tw})
        if already_sent(entries, fake):
            continue
        try:
            ai = classify_x_relevance(text, prompt)
            stats["ai_ok"] += 1
        except Exception as e:
            stats["errors"] += 1
            frow = {"at": utc_now_iso(), "jobType": "x", "source_name": "X", "error_summary": str(e)[:400]}
            append_failure(dash, frow)
            fail_ledger.append(frow)
            continue
        if ai.relevance != "relevant":
            row = {
                "at": utc_now_iso(),
                "category": "x",
                "source_name": "X",
                "title": text[:200],
                "decision": "skipped",
                "reason": f"{ai.relevance}:{ai.reason}",
                "link": link,
            }
            append_item_row(dash, row)
            item_ledger.append(row)
            continue
        line = format_x_line(text, link, ai.reason, ai.matched_keywords, ai.business_tags)
        ok, err = send_telegram_message(line)
        if not ok:
            stats["errors"] += 1
            frow = {"at": utc_now_iso(), "jobType": "x", "source_name": "X", "error_summary": err or "telegram"}
            append_failure(dash, frow)
            fail_ledger.append(frow)
            continue
        register_sent(
            entries,
            fake,
            {
                "source_id": "x_president",
                "category": "x",
                "relevance_score": ai.relevance_score,
                "reason": ai.reason,
                "matched_keywords": ai.matched_keywords,
                "business_tags": ai.business_tags,
            },
        )
        stats["sent"] += 1
        send_row = {
            "at": utc_now_iso(),
            "category": "x",
            "source_name": "X",
            "title": text[:200],
            "summary_short": None,
            "link": link,
            "reason": ai.reason,
            "matched_keywords": ai.matched_keywords,
        }
        append_send(dash, send_row)
        sent_row = {
            "at": send_row["at"],
            "category": "x",
            "source_name": "X",
            "title": text[:200],
            "decision": "sent",
            "reason": ai.reason,
            "link": link,
        }
        append_item_row(dash, sent_row)
        item_ledger.append(sent_row)

    if newest_id:
        checkpoint.setdefault("x", {})["last_tweet_id"] = newest_id
    return stats


def _run_youtube_job(
    storage: Storage,
    src_list: list[dict[str, Any]],
    entries: dict[str, Any],
    checkpoint: dict[str, Any],
    dash: dict[str, Any],
    item_ledger: list[dict[str, Any]],
    fail_ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    yt_src = next((s for s in src_list if s.get("source_id") == "ktv_youtube"), None)
    if not yt_src:
        raise RuntimeError("ktv_youtube missing in sources.json")
    prompt = _load_prompt(storage, "youtube_summary_prompt.txt")
    handle = _youtube_handle_from_source_url(str(yt_src.get("url") or "")) or "ktv_kr"
    ch = resolve_channel_id_for_handle(handle)
    vids = search_cabinet_videos(ch, max_results=10)
    processed = list((checkpoint.get("youtube") or {}).get("processed_video_ids") or [])
    proc_set = set(processed)
    stats = {"candidates": len(vids), "summarized": 0, "sent": 0, "errors": 0}

    for it in vids:
        idobj = it.get("id") or {}
        vid = idobj.get("videoId") if isinstance(idobj, dict) else None
        if not vid:
            continue
        if vid in proc_set:
            continue
        detail = get_video_detail(vid)
        sn = detail.get("snippet") or {}
        title = sn.get("title") or ""
        desc = sn.get("description") or ""
        link = f"https://www.youtube.com/watch?v={vid}"
        fake = ParsedItem(external_id=vid, title=title, link=link, published_at=sn.get("publishedAt"), raw={})
        if already_sent(entries, fake):
            proc_set.add(vid)
            continue
        transcript = ""
        t_avail = False
        try:
            summ = summarize_youtube(title, desc, transcript, prompt, transcript_available=t_avail)
            stats["summarized"] += 1
        except Exception as e:
            stats["errors"] += 1
            frow = {"at": utc_now_iso(), "jobType": "youtube", "source_name": "KTV", "error_summary": str(e)[:400]}
            append_failure(dash, frow)
            fail_ledger.append(frow)
            continue
        line = format_youtube_line(summ.summary_short, link, summ.summary_bullets, summ.caution, summ.matched_keywords)
        ok, err = send_telegram_message(line)
        if not ok:
            stats["errors"] += 1
            frow = {"at": utc_now_iso(), "jobType": "youtube", "source_name": "KTV", "error_summary": err or "telegram"}
            append_failure(dash, frow)
            fail_ledger.append(frow)
            continue
        register_sent(
            entries,
            fake,
            {
                "source_id": "ktv_youtube",
                "category": "youtube",
                "summary_short": summ.summary_short,
                "matched_keywords": summ.matched_keywords,
                "caution": summ.caution,
                "transcript_available": summ.transcript_available,
            },
        )
        stats["sent"] += 1
        proc_set.add(vid)
        send_row = {
            "at": utc_now_iso(),
            "category": "youtube",
            "source_name": "KTV",
            "title": title,
            "summary_short": summ.summary_short,
            "link": link,
            "reason": summ.caution,
            "matched_keywords": summ.matched_keywords,
        }
        append_send(dash, send_row)
        sent_row = {
            "at": send_row["at"],
            "category": "youtube",
            "source_name": "KTV",
            "title": title,
            "decision": "sent",
            "reason": "youtube_summary",
            "link": link,
        }
        append_item_row(dash, sent_row)
        item_ledger.append(sent_row)

    checkpoint.setdefault("youtube", {})["processed_video_ids"] = list(proc_set)[-500:]
    checkpoint["youtube"]["last_run_at"] = utc_now_iso()
    return stats
