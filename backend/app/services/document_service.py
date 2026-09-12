from pathlib import Path


SUPPORTED_EXTENSIONS = {".pdf", ".pptx"}


def validate_document(filename: str) -> Path:
    path = Path(filename)
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError("Only PDF and PPTX documents are supported")
    return path
