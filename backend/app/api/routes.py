from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["notewise"])


@router.get("/documents")
def list_documents() -> dict[str, list[dict[str, str]]]:
    return {"documents": []}


@router.post("/chat")
def chat() -> dict[str, str]:
    return {"answer": "RAG chat endpoint is ready to be connected."}
