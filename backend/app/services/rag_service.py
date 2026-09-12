from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter


class RAGService:
    """Coordinates document ingestion, retrieval, and answer generation."""

    def __init__(self, persist_directory: str = "./data/chroma") -> None:
        self.persist_directory = Path(persist_directory)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=120,
        )

    def split_text(self, text: str) -> list[str]:
        return self.text_splitter.split_text(text)


rag_service = RAGService()
