import os
from typing import Any, Optional

from db import ApiUsage


def _float_from_env(name: str, default: float = 0.0) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


INPUT_PRICE_PER_1M_TOKENS = _float_from_env("LLM_INPUT_PRICE_PER_1M_TOKENS")
OUTPUT_PRICE_PER_1M_TOKENS = _float_from_env("LLM_OUTPUT_PRICE_PER_1M_TOKENS")


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> float:
    input_cost = (prompt_tokens / 1_000_000) * INPUT_PRICE_PER_1M_TOKENS
    output_cost = (completion_tokens / 1_000_000) * OUTPUT_PRICE_PER_1M_TOKENS
    return round(input_cost + output_cost, 8)


def record_llm_usage(
    *,
    user_id: int,
    operation: str,
    model: str,
    response: Any,
    latency_ms: Optional[int] = None,
    document_processing_job_id: Optional[int] = None,
):
    usage = getattr(response, "usage", None)
    prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
    total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)

    ApiUsage.create(
        user_id=user_id,
        operation=operation,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        estimated_cost_usd=estimate_cost(prompt_tokens, completion_tokens),
        latency_ms=latency_ms,
        document_processing_job_id=document_processing_job_id,
    )
