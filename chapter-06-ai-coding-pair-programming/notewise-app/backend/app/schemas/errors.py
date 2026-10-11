from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

ErrorCode = Literal[
    "INVALID_REQUEST",
    "UNAUTHENTICATED",
    "TOKEN_EXPIRED",
    "TOKEN_INVALID",
    "NOT_FOUND",
    "STATE_CONFLICT",
    "ALREADY_SUBMITTED",
    "IDEMPOTENCY_CONFLICT",
    "FILE_TOO_LARGE",
    "UNSUPPORTED_FILE_TYPE",
    "VALIDATION_ERROR",
    "RATE_LIMITED",
    "AI_OUTPUT_INVALID",
    "AI_VALIDATION_FAILED",
    "AI_PROVIDER_UNAVAILABLE",
    "PROCESSING_UNAVAILABLE",
    "AI_TIMEOUT",
]


class ErrorDetail(BaseModel):
    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None
    request_id: UUID


class ErrorResponse(BaseModel):
    error: ErrorDetail
