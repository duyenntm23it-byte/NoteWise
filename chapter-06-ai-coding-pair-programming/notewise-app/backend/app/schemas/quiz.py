from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator


class QuizGenerateRequest(BaseModel):
    document_id: UUID
    num_questions: Annotated[int, Field(strict=True)]

    @model_validator(mode="after")
    def validate_question_count(self) -> "QuizGenerateRequest":
        if self.num_questions not in {5, 10}:
            raise ValueError("num_questions must be 5 or 10.")
        return self


# --- Schema CHỈ để gửi cho Gemini (response_schema) ---
# Không dùng extra="forbid" hay StrictInt ở đây: Gemini không hỗ trợ
# "additionalProperties" và sẽ trả lỗi 400. Kết quả trả về luôn được
# validate lại bằng GeneratedQuiz (chặt) bên dưới.
class GeminiQuestionSchema(BaseModel):
    question_text: str
    options: list[str] = Field(description="Exactly four distinct answer options.")
    correct_answer: int = Field(description="Zero-based index (0 to 3) of the correct option.")
    explanation: str
    source_excerpt: int = Field(description="Number of the excerpt that supports the answer.")


class GeminiQuizSchema(BaseModel):
    questions: list[GeminiQuestionSchema]


# --- Schema CHẶT để validate kết quả từ Gemini ---
class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_text: str
    options: list[str]
    correct_answer: StrictInt
    explanation: str
    source_excerpt: StrictInt


class GeneratedQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[GeneratedQuestion]


class QuizQuestionRead(BaseModel):
    id: UUID
    position: int
    question_text: str
    options: list[str]


class QuizRead(BaseModel):
    id: UUID
    title: str
    total_questions: int
    questions: list[QuizQuestionRead]


class QuizSummary(BaseModel):
    id: UUID
    title: str
    total_questions: int
    created_at: datetime
    latest_score: int | None


class SubmittedAnswer(BaseModel):
    question_id: UUID
    selected_index: Annotated[StrictInt, Field(ge=0, le=3)] | None = None


class QuizSubmitRequest(BaseModel):
    answers: list[SubmittedAnswer] = Field(max_length=10)

    @model_validator(mode="after")
    def question_ids_must_be_unique(self) -> "QuizSubmitRequest":
        question_ids = [answer.question_id for answer in self.answers]
        if len(question_ids) != len(set(question_ids)):
            raise ValueError("Each question may be answered only once.")
        return self


class QuizQuestionResult(BaseModel):
    question_id: UUID
    position: int
    question_text: str
    options: list[str]
    selected_index: int | None
    correct_answer: int
    is_correct: bool
    explanation: str
    source_document_title: str
    source_chunk_index: int | None
    source_page_number: int | None


class QuizAttemptRead(BaseModel):
    score: int
    total: int
    results: list[QuizQuestionResult]