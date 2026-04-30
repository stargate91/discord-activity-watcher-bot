import asyncpg
import datetime
import os
from config_loader import Config


def _to_naive_utc(value):
    """Normalize aware datetimes to naive UTC for PostgreSQL TIMESTAMP columns."""
    if value is None or not isinstance(value, datetime.datetime):
        return value
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


class MessageArchiveDB:
    def __init__(self, database_url=None):
        self.database_url = database_url or Config.DATABASE_URL
        self.pool = None

    async def initialize(self):
        """Initializes the connection pool and creates tables."""
        if not self.pool:
            self.pool = await asyncpg.create_pool(self.database_url)
            await self._create_table()

    async def close(self):
        if self.pool:
            await self.pool.close()

    async def _create_table(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id BIGINT PRIMARY KEY,
                    guild_id BIGINT,
                    channel_id BIGINT,
                    user_id BIGINT,
                    username TEXT,
                    content TEXT,
                    attachments TEXT,
                    timestamp TIMESTAMP,
                    is_bot BOOLEAN DEFAULT FALSE
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_guild ON messages(guild_id)")
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS channel_sync_state (
                    guild_id BIGINT,
                    channel_id BIGINT,
                    oldest_message_id BIGINT,
                    is_completed BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (guild_id, channel_id)
                )
            """)

    async def get_sync_state(self, guild_id, channel_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT oldest_message_id, is_completed FROM channel_sync_state WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
            if row:
                return {"oldest_message_id": row['oldest_message_id'], "is_completed": bool(row['is_completed'])}
            return {"oldest_message_id": None, "is_completed": False}

    async def update_sync_state(self, guild_id, channel_id, oldest_message_id, is_completed):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO channel_sync_state (guild_id, channel_id, oldest_message_id, is_completed)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT(guild_id, channel_id) DO UPDATE SET 
                oldest_message_id = EXCLUDED.oldest_message_id,
                is_completed = EXCLUDED.is_completed
            """, guild_id, channel_id, oldest_message_id, is_completed)

    async def insert_message(self, message_id, guild_id, channel_id, user_id, username, is_bot, content, attachments, timestamp):
        timestamp = _to_naive_utc(timestamp)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO messages (message_id, guild_id, channel_id, user_id, username, is_bot, content, attachments, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                ON CONFLICT (message_id) DO NOTHING
            """, message_id, guild_id, channel_id, user_id, username, bool(is_bot), content, attachments, timestamp)

    async def update_message_content(self, message_id, new_content):
        async with self.pool.acquire() as conn:
            await conn.execute("UPDATE messages SET content = $1 WHERE message_id = $2", new_content, message_id)

    async def get_message(self, message_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT user_id, username, is_bot, content, attachments, timestamp FROM messages WHERE message_id = $1", message_id)
            if row:
                return {
                    "user_id": row['user_id'],
                    "username": row['username'],
                    "is_bot": bool(row['is_bot']),
                    "content": row['content'],
                    "attachments": row['attachments'],
                    "timestamp": row['timestamp']
                }
            return None

    async def prune_database(self, retention_days=None):
        deleted_count = 0
        if retention_days and retention_days > 0:
            cutoff_date = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days))
            async with self.pool.acquire() as conn:
                res = await conn.execute("DELETE FROM messages WHERE timestamp < $1", cutoff_date)
                # asyncpg returns 'DELETE N'
                try:
                    deleted_count = int(res.split(' ')[1])
                except:
                    deleted_count = 0
        return deleted_count
