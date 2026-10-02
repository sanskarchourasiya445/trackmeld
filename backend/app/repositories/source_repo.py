from typing import Optional, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.app.db.models.source import SourceDocumentModel
from backend.app.repositories.base import BaseRepository


class SourceDocumentRepository(BaseRepository[SourceDocumentModel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(SourceDocumentModel, session)

    async def get_by_sha256(self, sha256: str) -> Optional[SourceDocumentModel]:
        stmt = select(SourceDocumentModel).where(SourceDocumentModel.sha256 == sha256)
        result = await self.session.execute(stmt)
        return result.scalars().first()
