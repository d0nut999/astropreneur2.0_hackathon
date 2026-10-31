"""LLM wrapper for OpenAI-compatible endpoints."""
import hashlib
import json
import os
from pathlib import Path
from typing import Type
from pydantic import BaseModel
from openai import OpenAI
from .config import settings
from .audit import log_audit
from sqlmodel import Session


class LLMError(Exception):
    """LLM-related error."""
    pass


def _get_cache_path(key: str) -> Path:
    """Get cache file path for a key."""
    cache_dir = Path("./data/llm_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{key}.json"


def _load_cache(key: str) -> dict | None:
    """Load from cache if enabled."""
    if not settings.llm_cache_enabled:
        return None

    path = _get_cache_path(key)
    if path.exists():
        with open(path, "r") as f:
            return json.load(f)
    return None


def _save_cache(key: str, data: dict):
    """Save to cache."""
    if not settings.llm_cache_enabled:
        return

    path = _get_cache_path(key)
    with open(path, "w") as f:
        json.dump(data, f)


def complete_json(
    task: str,
    system: str,
    user: str,
    schema: Type[BaseModel],
    prompt_version: str = "v1",
    db: Session = None,
) -> BaseModel:
    """
    Call LLM with structured JSON output.

    Args:
        task: Task name (e.g., "score", "evaluate")
        system: System prompt
        user: User prompt
        schema: Pydantic schema to validate output
        prompt_version: Prompt version for caching
        db: Database session for audit logging

    Returns:
        Validated Pydantic model

    Raises:
        LLMError: If LLM not configured, returns invalid JSON, or retries exhausted
    """
    if not settings.llm_api_key:
        raise LLMError(
            "LLM not configured. Set LLM_API_KEY in environment."
        )

    # Cache key: hash of (model, prompt_version, system, user)
    cache_key = hashlib.sha256(
        f"{settings.llm_model}:{prompt_version}:{system}:{user}".encode()
    ).hexdigest()

    # Try cache
    if cached := _load_cache(cache_key):
        return schema.model_validate(cached)

    # Build client
    client = OpenAI(
        api_key=settings.llm_api_key,
        base_url=settings.llm_base_url,
        timeout=60,
    )

    # Models to try in order: main model, then fallbacks.
    # (Works with any OpenAI-compatible provider: Groq, Gemini, OpenRouter, Claude...)
    models = [settings.llm_model]
    if settings.llm_fallback_models:
        models += [m.strip() for m in settings.llm_fallback_models.split(",") if m.strip()]

    last_error = None
    for model in models:
        for _attempt in range(settings.llm_max_attempts):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    temperature=settings.llm_temperature,
                    response_format={"type": "json_object"},
                )
                content = response.choices[0].message.content or ""
                output_json = _extract_json(content)
                result = schema.model_validate(output_json)
            except (json.JSONDecodeError, ValueError) as e:
                # Bad JSON or wrong shape -> retry same model
                last_error = f"{model}: {e}"
                continue
            except Exception as e:
                # API error (rate limit, model not found...) -> try next model
                last_error = f"{model}: {e}"
                break

            _save_cache(cache_key, output_json)
            if db:
                log_audit(
                    db,
                    actor="ai",
                    action=task,
                    entity="llm_call",
                    entity_id=0,
                    payload={"model": model, "prompt_version": prompt_version, "cached": False},
                )
            return result

    raise LLMError(f"All LLM attempts failed. Last error: {last_error}")


def _extract_json(content: str) -> dict:
    """Parse JSON even if the model wrapped it in ```json fences or added text."""
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:]
    start, end = content.find("{"), content.rfind("}")
    if start == -1 or end == -1:
        raise json.JSONDecodeError("No JSON object found", content, 0)
    return json.loads(content[start : end + 1])
