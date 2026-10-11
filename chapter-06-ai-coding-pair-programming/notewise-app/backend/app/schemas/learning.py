from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


SummaryStatus = Literal["QUEUED", "PROCESSING", "READY", "FAILED", "DELETED"]


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    status: SummaryStatus
    content: str | None
    failure_code: str | None
    created_at: datetime


class SummaryAccepted(BaseModel):
    summary: SummaryResponse
    job_id: UUID


class JobAccepted(BaseModel):
    job_id: UUID
    status: Literal["QUEUED", "RETRY_WAIT"]


class QuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=4000)

    @field_validator("question")
    @classmethod
    def reject_blank_question(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Question cannot be blank.")
        return value


class Citation(BaseModel):
    chunk_id: UUID
    page_number: int | None = Field(ge=1)
    section: str | None = None
    excerpt: str = Field(max_length=1200)


class AnsweredResponse(BaseModel):
    status: Literal["answered"] = "answered"
    answer: str = Field(min_length=1)
    citations: list[Citation] = Field(min_length=1)


class InsufficientEvidenceResponse(BaseModel):
    status: Literal["insufficient_evidence"] = "insufficient_evidence"
    answer: None = None
    citations: list[Citation] = Field(max_length=0)
    code: Literal["INSUFFICIENT_EVIDENCE"] = "INSUFFICIENT_EVIDENCE"


QuestionResponse = Annotated[
    AnsweredResponse | InsufficientEvidenceResponse,
    Field(discriminator="status"),
]

QuizQuestionType = Literal["multiple_choice", "true_false", "fill_blank"]
QuizDifficulty = Literal["easy", "medium", "hard"]
QuizStatus = Literal["QUEUED", "PROCESSING", "READY", "FAILED", "DELETED"]
LearningEventType = Literal[
    "DOCUMENT_UPLOADED",
    "SUMMARY_CREATED",
    "QUESTION_ASKED",
    "QUIZ_SUBMITTED",
]


class AnalyticsOverview(BaseModel):
    average_score: float | None = Field(ge=0, le=100)
    document_count: int = Field(ge=0)
    completed_quiz_count: int = Field(ge=0)


class AccuracyAnalytics(BaseModel):
    accuracy: float | None = Field(ge=0, le=100)
    correct_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)


class WeakTopic(BaseModel):
    topic: str
    accuracy: float | None = Field(ge=0, le=100)
    attempts: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    sufficient_data: bool
    is_weak: bool
    reason: str | None


class WeakTopicPage(BaseModel):
    items: list[WeakTopic]


class Recommendation(BaseModel):
    id: UUID
    topic: str
    action: str
    reason: str
    document_id: UUID | None
    chunk_id: UUID | None
    page_start: int | None = Field(ge=1)
    page_end: int | None = Field(ge=1)
    created_at: datetime


class RecommendationPage(BaseModel):
    items: list[Recommendation]


class LearningHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: LearningEventType
    document_id: UUID | None
    document_title: str | None
    occurred_at: datetime
    details: dict[str, Any]


class LearningHistoryPage(BaseModel):
    items: list[LearningHistoryItem]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class DocumentChunkResponse(BaseModel):
    id: UUID
    document_id: UUID
    content: str
    page_number: int | None = Field(ge=1)
    section: str | None


class QuizCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_count: int = Field(ge=5, le=20)
    question_types: list[QuizQuestionType] = Field(
        min_length=1,
        max_length=3,
        json_schema_extra={"uniqueItems": True},
    )
    difficulty: QuizDifficulty
    topic: str | None = Field(default=None, max_length=200)

    @field_validator("question_types")
    @classmethod
    def require_unique_types(
        cls,
        value: list[QuizQuestionType],
    ) -> list[QuizQuestionType]:
        if len(value) != len(set(value)):
            raise ValueError("Question types must be unique.")
        return value

    @field_validator("topic")
    @classmethod
    def normalize_topic(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class PublicQuizQuestion(BaseModel):
    id: UUID
    position: int
    question: str
    question_type: QuizQuestionType
    options: list[str]
    citation: Citation


class QuizResponse(BaseModel):
    id: UUID
    title: str
    status: QuizStatus
    questions: list[PublicQuizQuestion]
    failure_code: str | None = None


class QuizAccepted(BaseModel):
    quiz_id: UUID
    status: QuizStatus
    job_id: UUID


class QuizFeedback(BaseModel):
    question_id: UUID
    is_correct: bool
    explanation: str | None = None
    citation: Citation | None = None
    submitted_answer: str | int | None = None
    correct_answer: str | int | list[str] | None = None


class QuizResult(BaseModel):
    attempt_id: UUID
    score: float = Field(ge=0, le=100)
    correct_count: int = Field(ge=0)
    answered_count: int = Field(ge=0)
    skipped_count: int = Field(ge=0)
    submitted_at: datetime
    feedback: list[QuizFeedback]


class QuizAttemptResponse(BaseModel):
    id: UUID
    quiz_id: UUID
    status: Literal["IN_PROGRESS", "SUBMITTED"]
    questions: list[PublicQuizQuestion]
    result: QuizResult | None = None


class QuizSubmitAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: UUID
    answer: str | int


class QuizSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[QuizSubmitAnswer]
