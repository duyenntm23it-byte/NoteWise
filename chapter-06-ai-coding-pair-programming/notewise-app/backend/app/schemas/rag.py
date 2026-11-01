from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class RagQuery(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[UUID] | None = Field(default=None, max_length=100)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, question: str) -> str:
        question = question.strip()
        if not question:
            raise ValueError("Question must not be blank.")
        return question


class CitationRead(BaseModel):
    reference: int
    document_id: UUID
    document_title: str
    chunk_index: int
    page_number: int | None
    content: str


class RagAnswer(BaseModel):
    answer: str
    citations: list[CitationRead]
