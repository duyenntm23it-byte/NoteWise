# from collections.abc import Sequence
# from typing import Protocol
# import asyncio
# import os

# from google import genai
# from app.core.config import settings

# EMBEDDING_DIMENSIONS = 768
# EMBEDDING_MODEL = "text-embedding-005"


# class EmbeddingError(Exception):
#     pass


# class EmbeddingServiceUnavailable(EmbeddingError):
#     pass


# class EmbeddingProviderError(EmbeddingError):
#     pass


# class EmbeddingDimensionError(EmbeddingError):
#     pass


# class EmbeddingService(Protocol):
#     async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...


# class GoogleGeminiEmbeddingService:
#     def __init__(self, api_key: str | None) -> None:
#         self._api_key = api_key

#     async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
#         if not self._api_key:
#             raise EmbeddingServiceUnavailable(
#                 "Document embeddings are unavailable; configure GOOGLE_API_KEY."
#             )

#         try:
#             client = genai.Client(api_key=self._api_key)
            
#             vectors = []
#             for text in texts:
#                 response = await asyncio.to_thread(
#                     client.models.embed_content,
#                     model=EMBEDDING_MODEL,
#                     contents=text,
#                 )
#                 vectors.append(response.embedding.values)
                
#         except Exception as exc:
#             print(f"=== CHI TIẾT LỖI GEMINI EMBEDDING: {exc} ===")
#             import traceback
#             traceback.print_exc()
#             raise EmbeddingProviderError(
#                 "The embedding provider could not process this document."
#             ) from exc

#         validate_embedding_dimensions(vectors, len(texts))
#         return vectors


# def validate_embedding_dimensions(
#     vectors: Sequence[Sequence[float]], expected_count: int
# ) -> None:
#     if len(vectors) != expected_count:
#         raise EmbeddingDimensionError("Embedding provider returned an unexpected vector count.")
#     if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
#         raise EmbeddingDimensionError(
#             f"Embedding vectors must contain exactly {EMBEDDING_DIMENSIONS} dimensions."
#         )


# def get_embedding_service() -> EmbeddingService:
#     api_key = (
#         settings.google_api_key.get_secret_value() 
#         if hasattr(settings, "google_api_key") and settings.google_api_key is not None 
#         else getattr(settings, "google_api_key", None)
#     )
#     if not api_key:
#         api_key = os.getenv("GOOGLE_API_KEY")
        
#     return GoogleGeminiEmbeddingService(api_key)

import asyncio
import logging
import math
import os
from collections.abc import Sequence
from typing import Protocol

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 768
EMBEDDING_MODEL = "gemini-embedding-001"

BATCH_SIZE = 50
MAX_RETRIES = 5
RETRYABLE_STATUS_CODES = {429, 500, 503}


class EmbeddingError(Exception):
    pass


class EmbeddingServiceUnavailable(EmbeddingError):
    pass


class EmbeddingProviderError(EmbeddingError):
    pass


class EmbeddingDimensionError(EmbeddingError):
    pass


class EmbeddingService(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


def _normalize(vector: Sequence[float]) -> list[float]:
    # Với số chiều < 3072, Gemini không tự chuẩn hóa vector,
    # nên phải normalize thủ công để cosine search chính xác.
    norm = math.sqrt(sum(x * x for x in vector))
    if norm == 0:
        return list(vector)
    return [x / norm for x in vector]


class GoogleGeminiEmbeddingService:
    def __init__(self, api_key: str | None) -> None:
        self._api_key = api_key

    def _get_client(self) -> genai.Client:
        if not self._api_key:
            raise EmbeddingServiceUnavailable(
                "Document embeddings are unavailable; configure GOOGLE_API_KEY."
            )
        return genai.Client(api_key=self._api_key)

    async def _embed_batch(
        self, client: genai.Client, batch: list[str], task_type: str
    ) -> list[list[float]]:
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.to_thread(
                    client.models.embed_content,
                    model=EMBEDDING_MODEL,
                    contents=batch,
                    config=types.EmbedContentConfig(
                        task_type=task_type,
                        output_dimensionality=EMBEDDING_DIMENSIONS,
                    ),
                )
                return [_normalize(e.values) for e in response.embeddings]
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                status = getattr(exc, "code", None)
                if status in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES - 1:
                    wait = 2**attempt * 2  # 2s, 4s, 8s, 16s
                    logger.warning(
                        "Gemini embedding lỗi %s, thử lại sau %ss (lần %s/%s)",
                        status, wait, attempt + 1, MAX_RETRIES,
                    )
                    await asyncio.sleep(wait)
                    continue
                break

        logger.exception("Gemini embedding failed: %s", last_exc)
        raise EmbeddingProviderError(
            "The embedding provider could not process this document."
        ) from last_exc

    async def _embed(self, texts: Sequence[str], task_type: str) -> list[list[float]]:
        client = self._get_client()
        items = list(texts)
        vectors: list[list[float]] = []

        for start in range(0, len(items), BATCH_SIZE):
            batch = items[start : start + BATCH_SIZE]
            vectors.extend(await self._embed_batch(client, batch, task_type))

        validate_embedding_dimensions(vectors, len(items))
        return vectors

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return await self._embed(texts, task_type="RETRIEVAL_DOCUMENT")

    async def embed_query(self, text: str) -> list[float]:
        # Dùng cho Slice 3 (RAG search): embed câu hỏi của người dùng
        vectors = await self._embed([text], task_type="RETRIEVAL_QUERY")
        return vectors[0]


def validate_embedding_dimensions(
    vectors: Sequence[Sequence[float]], expected_count: int
) -> None:
    if len(vectors) != expected_count:
        raise EmbeddingDimensionError(
            "Embedding provider returned an unexpected vector count."
        )
    if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
        raise EmbeddingDimensionError(
            f"Embedding vectors must contain exactly {EMBEDDING_DIMENSIONS} dimensions."
        )


def get_embedding_service() -> EmbeddingService:
    api_key = (
        settings.google_api_key.get_secret_value()
        if settings.google_api_key is not None
        else os.getenv("GOOGLE_API_KEY")
    )
    return GoogleGeminiEmbeddingService(api_key or None)