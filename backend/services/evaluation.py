import json
from time import perf_counter
from typing import Literal, TypedDict

from anyio import sleep

from backend.services.cost_tracking import record_llm_usage
from backend.services.openai_client import openai_client


class GroundednessResult(TypedDict):
    label: Literal["Grounded", "Hallucination Risk"]
    score: float
    reason: str


EVALUATE_ANSWER_SYSTEM_PROMPT = """
You evaluate whether an answer is grounded in the supplied document excerpts.
Score faithfulness from 0.0 to 1.0:
- 1.0 means every material claim is directly supported by the excerpts.
- 0.0 means the answer is mostly unsupported or contradicts the excerpts.
Return strict JSON only:
{"score": 0.0, "reason": "short explanation"}
"""


async def evaluate_groundedness(
    question: str,
    answer: str,
    references: list[str],
    user_id: int,
) -> GroundednessResult:
    if not references:
        return {
            "label": "Hallucination Risk",
            "score": 0.0,
            "reason": "No document references were retrieved for this answer.",
        }

    user_prompt = "\n\n".join(
        [
            f"Question:\n{question}",
            f"Answer:\n{answer}",
            "Document excerpts:",
            "\n".join(f"{index + 1}. {reference}" for index, reference in enumerate(references)),
        ]
    )

    total_retries = 0
    while True:
        try:
            model = "llama-3.3-70b-versatile"
            started_at = perf_counter()
            output = await openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": EVALUATE_ANSWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                top_p=1,
                response_format={"type": "json_object"},
            )
            latency_ms = int((perf_counter() - started_at) * 1000)
            record_llm_usage(
                user_id=user_id,
                operation="groundedness_evaluation",
                model=model,
                response=output,
                latency_ms=latency_ms,
            )
            content = output.choices[0].message.content or "{}"
            parsed = json.loads(content)
            score = max(0.0, min(1.0, float(parsed.get("score", 0.0))))
            return {
                "label": "Grounded" if score >= 0.75 else "Hallucination Risk",
                "score": score,
                "reason": str(parsed.get("reason", "No evaluator reason returned.")),
            }
        except Exception as exc:
            total_retries += 1
            if total_retries > 3:
                return {
                    "label": "Hallucination Risk",
                    "score": 0.0,
                    "reason": f"Groundedness evaluator failed: {exc}",
                }
            await sleep(1)
