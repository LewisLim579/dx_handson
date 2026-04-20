from __future__ import annotations

import json
import re
from typing import Any

import requests
from openai import AzureOpenAI

from clipper.models import XAIResult, YouTubeAIResult
from clipper.secrets import get_secret


def _use_azure() -> bool:
    ep = get_secret("AZURE_OPENAI_ENDPOINT")
    key = get_secret("AZURE_OPENAI_API_KEY")
    return bool(ep and key)


def _azure_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    endpoint = (get_secret("AZURE_OPENAI_ENDPOINT") or "").rstrip("/") + "/"
    key = get_secret("AZURE_OPENAI_API_KEY")
    if not key:
        raise RuntimeError("AZURE_OPENAI_API_KEY missing")
    deployment = get_secret("AZURE_OPENAI_DEPLOYMENT") or "lewis-gpt-5"
    api_version = get_secret("AZURE_OPENAI_API_VERSION") or "2024-12-01-preview"
    max_tok = int(get_secret("AZURE_OPENAI_MAX_TOKENS") or "4096")

    client = AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=key,
        api_version=api_version,
    )

    def _call(*, json_mode: bool, use_temp: bool) -> Any:
        kw: dict[str, Any] = {
            "model": deployment,
            "messages": messages,
            "max_completion_tokens": max_tok,
        }
        if use_temp:
            kw["temperature"] = temperature
        if json_mode:
            kw["response_format"] = {"type": "json_object"}
        return client.chat.completions.create(**kw)

    try:
        response = _call(json_mode=True, use_temp=True)
    except Exception:
        try:
            response = _call(json_mode=True, use_temp=False)
        except Exception:
            response = _call(json_mode=False, use_temp=False)

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("azure_openai_empty_content")
    return content


def _openai_compatible_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    key = get_secret("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY missing (또는 Azure OpenAI 환경 변수를 설정하세요)")
    url = get_secret("OPENAI_API_BASE") or "https://api.openai.com/v1/chat/completions"
    model = get_secret("OPENAI_MODEL") or "gpt-4o-mini"
    body = {
        "model": model,
        "temperature": temperature,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=body,
        timeout=120,
    )
    if r.status_code != 200:
        raise RuntimeError(f"openai_http_{r.status_code}: {r.text[:400]}")
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _llm_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    if _use_azure():
        return _azure_chat(messages, temperature=temperature)
    return _openai_compatible_chat(messages, temperature=temperature)


def _parse_json_loose(raw: str) -> dict[str, Any]:
    raw = raw.strip()
    m = re.search(r"\{[\s\S]*\}", raw)
    if m:
        raw = m.group(0)
    return json.loads(raw)


def classify_x_relevance(tweet_text: str, prompt_template: str) -> XAIResult:
    prompt = prompt_template.replace("{{tweet_text}}", tweet_text)
    content = _llm_chat(
        [
            {"role": "system", "content": "You output JSON only."},
            {"role": "user", "content": prompt},
        ]
    )
    d = _parse_json_loose(content)
    rel = str(d.get("relevance") or d.get("classification") or "uncertain").lower()
    if rel not in ("relevant", "irrelevant", "uncertain"):
        rel = "uncertain"
    score = float(d.get("score", d.get("relevance_score", 0.5)))
    reason = str(d.get("reason", ""))[:500]
    mk = d.get("matched_keywords") or []
    bt = d.get("business_tags") or []
    if isinstance(mk, str):
        mk = [mk]
    if isinstance(bt, str):
        bt = [bt]
    return XAIResult(
        relevance=rel,  # type: ignore[arg-type]
        relevance_score=score,
        reason=reason,
        matched_keywords=[str(x) for x in mk][:50],
        business_tags=[str(x) for x in bt][:50],
    )


def summarize_youtube(
    title: str,
    description: str,
    transcript: str,
    prompt_template: str,
    transcript_available: bool,
) -> YouTubeAIResult:
    prompt = (
        prompt_template.replace("{{title}}", title)
        .replace("{{description}}", description)
        .replace("{{transcript}}", transcript or "(없음)")
    )
    content = _llm_chat(
        [
            {"role": "system", "content": "You output JSON only. Korean summaries."},
            {"role": "user", "content": prompt},
        ]
    )
    d = _parse_json_loose(content)
    bullets = d.get("summary_bullets") or []
    if isinstance(bullets, str):
        bullets = [bullets]
    mk = d.get("matched_keywords") or []
    if isinstance(mk, str):
        mk = [mk]
    return YouTubeAIResult(
        summary_short=str(d.get("summary_short", ""))[:500],
        summary_bullets=[str(x) for x in bullets][:12],
        matched_keywords=[str(x) for x in mk][:50],
        caution=str(d.get("caution", ""))[:500],
        transcript_available=transcript_available,
    )
