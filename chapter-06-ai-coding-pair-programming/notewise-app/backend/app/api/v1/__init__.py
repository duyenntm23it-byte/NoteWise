from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.materials import router as materials_router
from app.api.v1.quizzes import router as quizzes_router
from app.api.v1.rag import router as rag_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(materials_router)
api_router.include_router(rag_router)
api_router.include_router(quizzes_router)
