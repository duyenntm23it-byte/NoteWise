from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.core.db import get_db_session
from app.models.user import User
from app.schemas.rag import CitationRead, RagAnswer, RagQuery
from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProviderError,
    EmbeddingService,
    EmbeddingServiceUnavailable,
    get_embedding_service,
)
from app.services.rag import (
    AnswerProviderError,
    AnswerService,
    AnswerServiceUnavailable,
    answer_question,
    get_answer_service,
)

router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RagAnswer)
async def query_documents(
    payload: RagQuery,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
    answer_service: Annotated[AnswerService, Depends(get_answer_service)],
) -> RagAnswer:
    try:
        answer, citations = await answer_question(
            session,
            user_id=current_user.id,
            question=payload.question,
            document_ids=payload.document_ids,
            embedding_service=embedding_service,
            answer_service=answer_service,
        )
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except EmbeddingServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (EmbeddingProviderError, EmbeddingDimensionError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except AnswerServiceUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AnswerProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    return RagAnswer(
        answer=answer,
        citations=[CitationRead.model_validate(citation) for citation in citations],
    )
