import streamlit as st

from frontend.api_client import ApiClientError, get
from frontend.auth import require_login


st.title("Admin / Monitoring")

current_user = require_login()
if not current_user.is_admin:
    st.error("You need admin access to view monitoring.")
    st.stop()


def currency(value: float) -> str:
    return f"${value:,.4f}"


try:
    metrics = get("/admin/monitoring")
except ApiClientError as exc:
    st.error(str(exc))
    st.stop()

if metrics["pricing_input_per_1m"] == 0 and metrics["pricing_output_per_1m"] == 0:
    st.info(
        "API cost estimates are currently $0 because LLM_INPUT_PRICE_PER_1M_TOKENS "
        "and LLM_OUTPUT_PRICE_PER_1M_TOKENS are not configured."
    )

st.subheader("System Health")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total users", metrics["total_users"])
col2.metric("Documents uploaded", metrics["documents_uploaded"])
col3.metric("Questions today", metrics["questions_today"])
col4.metric("Failed document jobs", metrics["failed_document_jobs"])

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg answer latency", f"{metrics['avg_answer_latency_ms']:,.0f} ms")
col2.metric("Avg faithfulness", f"{metrics['avg_faithfulness_score']:.0%}")
col3.metric("Hallucination risk", f"{metrics['hallucination_risk_percentage']:.1f}%")
col4.metric("API cost today", currency(metrics["api_cost_today_usd"]))

st.subheader("Cost Tracking")
col1, col2, col3 = st.columns(3)
col1.metric("Tokens today", f"{metrics['tokens_today']:,.0f}")
col2.metric("Avg tokens / query", f"{metrics['avg_tokens_per_query']:,.0f}")
col3.metric(
    "Pricing",
    f"${metrics['pricing_input_per_1m']:g}/${metrics['pricing_output_per_1m']:g} per 1M",
)

st.write("Daily cost summary")
st.dataframe(
    [
        {
            "Date": row["date"],
            "Input tokens": row["input_tokens"],
            "Output tokens": row["output_tokens"],
            "Total tokens": row["total_tokens"],
            "Estimated cost": currency(row["estimated_cost_usd"]),
        }
        for row in metrics["daily_cost_summary"]
    ],
    use_container_width=True,
)

st.write("Estimated cost per user / day")
st.dataframe(
    [
        {
            "User": row["user"],
            "Date": row["date"],
            "Total tokens": row["total_tokens"],
            "Estimated cost": currency(row["estimated_cost_usd"]),
        }
        for row in metrics["user_daily_costs"]
    ],
    use_container_width=True,
)

st.write("Estimated cost per document ingestion")
st.dataframe(
    [
        {
            "Document": row["document"],
            "User": row["user"],
            "Total tokens": row["total_tokens"],
            "Estimated cost": currency(row["estimated_cost_usd"]),
            "Status": row["status"],
        }
        for row in metrics["document_ingestion_costs"]
    ],
    use_container_width=True,
)

st.subheader("LLM Operations")
st.dataframe(
    [
        {
            "Operation": row["operation"],
            "Calls": row["calls"],
            "Avg latency": f"{row['avg_latency_ms']:,.0f} ms",
            "Total tokens": row["total_tokens"],
            "Estimated cost": currency(row["estimated_cost_usd"]),
        }
        for row in metrics["llm_operations"]
    ],
    use_container_width=True,
)
