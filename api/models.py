from pydantic import BaseModel, Field
from typing import Optional, List, Any


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    session_id: Optional[str] = None


class CreateSessionRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=100)
    industry: str = Field(min_length=1)
    categories: List[str] = Field(min_length=2, max_length=8)
    description: Optional[str] = ""
    urgency_definition: Optional[str] = ""


class CreateSessionResponse(BaseModel):
    session_id: str
    profile: dict
    created_at: str
    user_id: Optional[str] = None


class AnalyseTextRequest(BaseModel):
    session_id: str
    raw_text: str = Field(min_length=1)


class PreprocessingSummary(BaseModel):
    input_count: int
    final_count: int
    noise_removed: int
    exact_duplicates_removed: int
    near_duplicates_removed: int
    short_removed: int


class AnalyseResponse(BaseModel):
    session_id: str
    total_classified: int
    total_failed: int
    gemini_fallback_count: int
    failed_batches: List[Any]
    preprocessing: PreprocessingSummary


class DashboardResponse(BaseModel):
    session_id: str
    profile: dict
    dashboard_data: dict
    classification_done: bool
    total_classified: int


class ActionPlanResponse(BaseModel):
    session_id: str
    success: bool
    result: Optional[dict]
    health_score: int
    health_label: str
    provider: Optional[str]
    error: Optional[str]


class SessionSummary(BaseModel):
    session_id: str
    label: str
    created_at: str
    total_reviews: int
    overall_score: float


class SessionsListResponse(BaseModel):
    sessions: List[SessionSummary]
    total: int


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    modules: List[str]
