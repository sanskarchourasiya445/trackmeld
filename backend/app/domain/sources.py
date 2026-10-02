from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.app.domain.enums import SourceClass


class SourceDocument(BaseModel):
    """Authoritative source publication metadata."""
    source_id: str = Field(..., description="Unique alphanumeric identifier (e.g. SRC-TAG-2023-TBL-01)")
    title: str = Field(..., description="Document or publication title")
    publisher: str = Field(..., description="Publishing body (e.g. Railway Board, Ministry of Railways)")
    organization: str = Field(..., description="Railway organization (e.g. Indian Railways)")
    source_class: SourceClass = Field(..., description="Source authority class")
    source_url: Optional[str] = Field(default=None, description="Official online URL")
    local_path: Optional[str] = Field(default=None, description="Local archive path in data/raw/")
    file_size_bytes: Optional[int] = Field(default=None, ge=0, description="File size in bytes")
    document_date: Optional[str] = Field(default=None, description="Document publication date")
    version: Optional[str] = Field(default=None, description="Edition or version string")
    downloaded_at: Optional[datetime] = Field(default=None, description="Timestamp of archiving")
    sha256: str = Field(..., description="Cryptographic SHA-256 checksum of raw archive")
    data_types: List[str] = Field(default_factory=list, description="Categories of data contained")
    authority_level: str = Field(..., description="Statutory or operational authority classification")
    notes: Optional[str] = Field(default=None, description="Cataloging notes and scope")
