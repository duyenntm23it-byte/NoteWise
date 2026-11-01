from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DocumentRead(BaseModel):
    id: UUID
    title: str
    file_type: str
    status: str
    created_at: datetime
    chunk_count: int

    model_config = ConfigDict(from_attributes=True)
