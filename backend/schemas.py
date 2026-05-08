from typing import List, Optional

from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=8)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool


class QuestionQuotaResponse(BaseModel):
    daily_limit: int
    remaining_questions: int


class DocumentResponse(BaseModel):
    id: int
    name: str
    tags: List[str] = []


class DocumentUploadResponse(BaseModel):
    job_id: int
    status: str
    document_name: str


class JobResponse(BaseModel):
    id: int
    document_name: str
    status: str
    progress: int
    message: str
    error: Optional[str] = None
    created_at: str
    updated_at: str


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    document_id: Optional[int] = None
    selected_document_name: str = "All Documents"


class ChatMessageResponse(BaseModel):
    role: str
    content: str
    references: Optional[List[str]] = None
    groundedness_label: Optional[str] = None
    groundedness_score: Optional[float] = None
    groundedness_reason: Optional[str] = None


class ChatAskResponse(BaseModel):
    answer: str
    groundedness_label: str
    groundedness_score: float
    groundedness_reason: str
    references: List[str]
    remaining_questions: int


class MonitoringOverviewResponse(BaseModel):
    total_users: int
    documents_uploaded: int
    questions_today: int
    avg_answer_latency_ms: float
    avg_faithfulness_score: float
    hallucination_risk_percentage: float
    failed_document_jobs: int
    api_cost_today_usd: float
    tokens_today: int
    avg_tokens_per_query: float
    pricing_input_per_1m: float
    pricing_output_per_1m: float
    daily_cost_summary: List[dict]
    user_daily_costs: List[dict]
    document_ingestion_costs: List[dict]
    llm_operations: List[dict]


class TagRequest(BaseModel):
    name: str = Field(..., min_length=1)


class TagResponse(BaseModel):
    id: int
    name: str
