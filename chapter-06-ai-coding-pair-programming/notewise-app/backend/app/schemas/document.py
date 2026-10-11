from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

DocumentStatus = Literal["PROCESSING", "READY", "FAILED", "DELETING", "DELETED"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    media_type: Literal[
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ]
    status: DocumentStatus
    failure_code: str | None
    page_count: int | None = Field(ge=0)
    created_at: datetime
    updated_at: datetime


class DocumentPage(BaseModel):
    items: list[DocumentResponse]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)


class DocumentAccepted(BaseModel):
    document: DocumentResponse
    job_id: UUID


class DocumentDeletion(BaseModel):
    document_id: UUID
    status: Literal["DELETING", "DELETED"]


class JobAccepted(BaseModel):
    job_id: UUID
    status: Literal["QUEUED", "RETRY_WAIT"]
