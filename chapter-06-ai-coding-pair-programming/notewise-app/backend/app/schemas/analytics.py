from uuid import UUID

from pydantic import BaseModel


class DocumentAnalytics(BaseModel):
    document_id: UUID
    document_title: str
    quiz_count: int
    attempt_count: int
    average_score_percent: float | None
    accuracy_percent: float | None


class WeakArea(BaseModel):
    document_id: UUID
    document_title: str
    topic_label: str
    wrong_count: int
    total_count: int
    sample_questions: list[str]


class AnalyticsSummary(BaseModel):
    total_documents: int
    ready_documents: int
    total_quizzes: int
    total_attempts: int
    average_score_percent: float | None
    overall_accuracy_percent: float | None
    documents: list[DocumentAnalytics]
    weak_areas: list[WeakArea]
