from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from peewee import fn

from backend.schemas import MonitoringOverviewResponse
from backend.security import get_current_api_user
from backend.services.cost_tracking import INPUT_PRICE_PER_1M_TOKENS, OUTPUT_PRICE_PER_1M_TOKENS
from backend.db import ApiUsage, ChatMessages, DocumentProcessingJobs, Documents, QuestionUsage, Users, db


router = APIRouter(prefix="/admin", tags=["Admin"])


def require_admin(current_user: Users = Depends(get_current_api_user)) -> Users:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


def metric_value(value, fallback=0):
    return value if value is not None else fallback


@router.get("/monitoring", response_model=MonitoringOverviewResponse)
def monitoring_overview(_: Users = Depends(require_admin)):
    today = date.today().isoformat()

    assistant_answers = ChatMessages.select().where(ChatMessages.groundedness_label.is_null(False)).count()
    hallucination_risk_answers = (
        ChatMessages.select()
        .where(ChatMessages.groundedness_label == "Hallucination Risk")
        .count()
    )
    hallucination_risk_pct = (
        (hallucination_risk_answers / assistant_answers) * 100
        if assistant_answers
        else 0
    )

    daily_cost_rows = db.execute_sql(
        """
        SELECT
            created_at::date AS usage_date,
            SUM(prompt_tokens) AS input_tokens,
            SUM(completion_tokens) AS output_tokens,
            SUM(total_tokens) AS total_tokens,
            SUM(estimated_cost_usd) AS estimated_cost
        FROM api_usage
        GROUP BY created_at::date
        ORDER BY usage_date DESC
        LIMIT 14
        """
    ).fetchall()

    user_cost_rows = db.execute_sql(
        """
        SELECT
            users.email,
            api_usage.created_at::date AS usage_date,
            SUM(api_usage.total_tokens) AS total_tokens,
            SUM(api_usage.estimated_cost_usd) AS estimated_cost
        FROM api_usage
        JOIN users ON users.id = api_usage.user_id
        GROUP BY users.email, api_usage.created_at::date
        ORDER BY usage_date DESC, estimated_cost DESC
        LIMIT 25
        """
    ).fetchall()

    document_ingestion_rows = db.execute_sql(
        """
        SELECT
            document_processing_jobs.document_name,
            users.email,
            SUM(api_usage.total_tokens) AS total_tokens,
            SUM(api_usage.estimated_cost_usd) AS estimated_cost,
            MAX(document_processing_jobs.status) AS status
        FROM api_usage
        JOIN document_processing_jobs
            ON document_processing_jobs.id = api_usage.document_processing_job_id
        JOIN users ON users.id = api_usage.user_id
        WHERE api_usage.operation IN ('document_chunk_generation', 'document_tag_matching')
        GROUP BY document_processing_jobs.document_name, users.email, document_processing_jobs.id
        ORDER BY estimated_cost DESC
        LIMIT 25
        """
    ).fetchall()

    operation_rows = db.execute_sql(
        """
        SELECT
            operation,
            COUNT(*) AS calls,
            AVG(latency_ms) AS avg_latency_ms,
            SUM(total_tokens) AS total_tokens,
            SUM(estimated_cost_usd) AS estimated_cost
        FROM api_usage
        GROUP BY operation
        ORDER BY calls DESC
        """
    ).fetchall()

    return MonitoringOverviewResponse(
        total_users=Users.select().count(),
        documents_uploaded=Documents.select().count(),
        questions_today=int(metric_value(
            QuestionUsage.select(fn.SUM(QuestionUsage.count))
            .where(QuestionUsage.usage_date == today)
            .scalar()
        )),
        avg_answer_latency_ms=float(metric_value(
            ApiUsage.select(fn.AVG(ApiUsage.latency_ms))
            .where(ApiUsage.operation == "answer_generation")
            .scalar()
        )),
        avg_faithfulness_score=float(metric_value(
            ChatMessages.select(fn.AVG(ChatMessages.groundedness_score))
            .where(ChatMessages.groundedness_score.is_null(False))
            .scalar()
        )),
        hallucination_risk_percentage=float(hallucination_risk_pct),
        failed_document_jobs=DocumentProcessingJobs.select().where(DocumentProcessingJobs.status == "failed").count(),
        api_cost_today_usd=float(metric_value(
            ApiUsage.select(fn.SUM(ApiUsage.estimated_cost_usd))
            .where(fn.DATE(ApiUsage.created_at) == today)
            .scalar()
        )),
        tokens_today=int(metric_value(
            ApiUsage.select(fn.SUM(ApiUsage.total_tokens))
            .where(fn.DATE(ApiUsage.created_at) == today)
            .scalar()
        )),
        avg_tokens_per_query=float(metric_value(
            ApiUsage.select(fn.AVG(ApiUsage.total_tokens))
            .where(ApiUsage.operation == "answer_generation")
            .scalar()
        )),
        pricing_input_per_1m=INPUT_PRICE_PER_1M_TOKENS,
        pricing_output_per_1m=OUTPUT_PRICE_PER_1M_TOKENS,
        daily_cost_summary=[
            {
                "date": row[0].isoformat(),
                "input_tokens": int(row[1] or 0),
                "output_tokens": int(row[2] or 0),
                "total_tokens": int(row[3] or 0),
                "estimated_cost_usd": float(row[4] or 0),
            }
            for row in daily_cost_rows
        ],
        user_daily_costs=[
            {
                "user": row[0],
                "date": row[1].isoformat(),
                "total_tokens": int(row[2] or 0),
                "estimated_cost_usd": float(row[3] or 0),
            }
            for row in user_cost_rows
        ],
        document_ingestion_costs=[
            {
                "document": row[0],
                "user": row[1],
                "total_tokens": int(row[2] or 0),
                "estimated_cost_usd": float(row[3] or 0),
                "status": row[4],
            }
            for row in document_ingestion_rows
        ],
        llm_operations=[
            {
                "operation": row[0],
                "calls": int(row[1] or 0),
                "avg_latency_ms": float(row[2] or 0),
                "total_tokens": int(row[3] or 0),
                "estimated_cost_usd": float(row[4] or 0),
            }
            for row in operation_rows
        ],
    )
