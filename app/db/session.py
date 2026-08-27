"""Async engine, session factory, and schema bootstrap.

The engine is created lazily so that importing the app never opens a socket -
that keeps unit tests and `--help` style invocations fast, and it means a
missing database surfaces as a clean 503 at request time rather than a crash
at import time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.errors import DatabaseUnavailable
from app.core.logging import get_logger
from app.db.models import Base

log = get_logger(__name__)

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,  # survive Postgres restarts without a app restart
            pool_size=5,
            max_overflow=10,
        )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session.

    Any driver-level failure is translated into `DatabaseUnavailable` so the
    API returns a documented 503 with a fix hint instead of a raw traceback.
    """
    factory = get_sessionmaker()
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    except SQLAlchemyError as exc:
        log.error("db.session_failed", error=str(exc)[:400])
        raise DatabaseUnavailable(str(exc)[:200]) from exc


async def init_db() -> None:
    """Create the pgvector extension and any missing tables.

    Safe to run on every boot. Vector support is optional: if the extension is
    unavailable the app still starts and retrieval falls back to lexical-only,
    which is logged loudly rather than silently.
    """
    engine = get_engine()
    async with engine.begin() as conn:
        try:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        except SQLAlchemyError as exc:
            log.warning(
                "db.pgvector_unavailable",
                error=str(exc)[:300],
                impact="dense retrieval disabled; lexical BM25 still active",
            )
        await conn.run_sync(Base.metadata.create_all)
    log.info("db.ready", url=_redact(settings.database_url))


async def ping() -> bool:
    """Cheap liveness probe used by /api/health."""
    try:
        async with get_engine().connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - health must never raise
        log.warning("db.ping_failed", error=str(exc)[:300])
        return False


async def dispose_engine() -> None:
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


def _redact(url: str) -> str:
    """Strip credentials so a DSN can be logged safely."""
    if "@" not in url:
        return url
    scheme, _, rest = url.partition("://")
    _, _, host = rest.rpartition("@")
    return f"{scheme}://***@{host}"
