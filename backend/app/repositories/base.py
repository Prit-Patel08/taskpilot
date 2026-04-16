from sqlalchemy.ext.asyncio import AsyncSession


class RepositoryBase:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
