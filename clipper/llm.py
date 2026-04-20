from __future__ import annotations

import json
import re
from typing import Any

import requests
from openai import AzureOpenAI

from clipper.models import XAIResult, YouTubeAIResult
from clipper.secrets import get_secret


def _gemini_chat(messages: list[dict[str, str]], temperature: float = 0.2) -> str:
    try:
        import google.generativeai as genai
    except ImportError as e:
        raise RuntimeError(
            "Gemini를 쓰려면 패키지가 필요합니다: pip install google-generativeai"
        ) from e

    key = get_secret("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY missing")

    genai.configure(api_key=key)
    model_name = (get_secret("GEMINI_MODEL") or "gemini-1.5-flash").strip()

    system_chunks = [m["content"] for m in messages if m.get("role") == "system"]
    user_chunks = [m["content"] for m in messages if m.get("role") == "user"]
    user_text = "\n\n".join(user_chunks) if user_chunks else ""

    gm_kw: dict[str, Any] = {}
    if system_chunks:
        gm_kw["system_instruction"] = "\n".join(system_chunks)
    model = genai.GenerativeModel(model_name, **gm_kw)

    # JSON 전용 응답(지원 모델). 실패 시 일반 텍스트로 재시도.
    gen_cfg: dict[str, Any] = {
        "temperature": temperature,
        "response_mime_type": "application/json",
    }
    try:
        response = model.generate_content(user_text, generation_config=gen_cfg)
    except Exception:
        gen_cfg.pop("response_mime_type", None)
        response = model.generate_content(user_text, generation_config=gen_cfg)

    text = (response.text or "").strip()
    if not text:
        raise RuntimeError("gemini_empty_content")
    return text


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


def _llm_chat(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    *,
    for_youtube: bool = False,
) -> str:
    """LLM 호출. for_youtube=True 이고 LLM_PROVIDER=auto 이면 GEMINI_API_KEY가 있을 때 유튜브만 Gemini 우선."""
    mode = (get_secret("LLM_PROVIDER") or "auto").strip().lower()
    gemini_key = get_secret("GEMINI_API_KEY")

    if mode == "gemini":
        if not gemini_key:
            raise RuntimeError("LLM_PROVIDER=gemini 인데 GEMINI_API_KEY가 없습니다")
        return _gemini_chat(messages, temperature)

    if mode == "azure":
        if not _use_azure():
            raise RuntimeError("LLM_PROVIDER=azure 인데 AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_API_KEY가 없습니다")
        return _azure_chat(messages, temperature)

    if mode == "openai":
        if not get_secret("OPENAI_API_KEY"):
            raise RuntimeError("LLM_PROVIDER=openai 인데 OPENAI_API_KEY가 없습니다")
        return _openai_compatible_chat(messages, temperature)

    # --- auto ---
    if for_youtube and gemini_key:
        return _gemini_chat(messages, temperature)
    if _use_azure():
        return _azure_chat(messages, temperature)
    if get_secret("OPENAI_API_KEY"):
        return _openai_compatible_chat(messages, temperature)
    if gemini_key:
        return _gemini_chat(messages, temperature)
    raise RuntimeError(
        "LLM 키가 없습니다. GEMINI_API_KEY, 또는 AZURE_OPENAI_ENDPOINT+AZURE_OPENAI_API_KEY, "
        "또는 OPENAI_API_KEY 중 하나를 설정하세요."
    )


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
        ],
        for_youtube=False,
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
        ],
        for_youtube=True,
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
