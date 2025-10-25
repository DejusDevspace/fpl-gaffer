# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
# from fpl_gaffer.settings import settings
# from typing import AsyncGenerator
#
# engine = create_async_engine(
#     settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"),
#     echo=settings.DEBUG,
#     future=True,
#     pool_pre_ping=True,
# )
#
# async_session_local = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
#
# async def get_db() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session_local() as session:
#         yield session
#
#
# from .models import Base
#
# __all__ = ["Base"]
