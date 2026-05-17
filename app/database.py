import asyncpg
import logging

log = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_messages (
    id          SERIAL PRIMARY KEY,
    message_id  BIGINT      NOT NULL,
    channel_id  TEXT        NOT NULL,
    text_preview TEXT,
    seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (message_id, channel_id)
);

CREATE TABLE IF NOT EXISTS vacancies (
    id          SERIAL PRIMARY KEY,
    message_id  BIGINT      NOT NULL,
    channel_id  TEXT        NOT NULL,
    text        TEXT,
    sent_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (message_id, channel_id)
);
"""


class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: asyncpg.Pool | None = None

    async def init(self):
        self._pool = await asyncpg.create_pool(self._dsn, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(CREATE_TABLE_SQL)
        log.info("✅ БД ініціалізована")

    async def is_seen(self, message_id: int, channel_id: str) -> bool:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM seen_messages WHERE message_id=$1 AND channel_id=$2",
                message_id, channel_id,
            )
            return row is not None

    async def mark_seen(self, message_id: int, channel_id: str, text_preview: str = ""):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO seen_messages (message_id, channel_id, text_preview)
                VALUES ($1, $2, $3)
                ON CONFLICT (message_id, channel_id) DO NOTHING
                """,
                message_id, channel_id, text_preview,
            )

    async def save_vacancy(self, message_id: int, channel_id: str, text: str):
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO vacancies (message_id, channel_id, text)
                VALUES ($1, $2, $3)
                ON CONFLICT (message_id, channel_id) DO NOTHING
                """,
                message_id, channel_id, text,
            )

    async def get_recent_vacancies(self, limit: int = 20) -> list[dict]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM vacancies ORDER BY sent_at DESC LIMIT $1", limit
            )
            return [dict(r) for r in rows]

    async def close(self):
        if self._pool:
            await self._pool.close()
