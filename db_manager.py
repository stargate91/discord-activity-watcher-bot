import asyncpg
import datetime
import os
import asyncio
import json
from config_loader import Config
from core.logger import log


def _to_naive_utc(value):
    """Normalize aware datetimes to naive UTC for PostgreSQL TIMESTAMP columns."""
    if value is None or not isinstance(value, datetime.datetime):
        return value
    if value.tzinfo is None:
        return value
    return value.astimezone(datetime.timezone.utc).replace(tzinfo=None)


class DBManager:
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
            # user_activity: Stores the overall numbers for each person (messages, voice time, etc.)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id BIGINT,
                    guild_id BIGINT,
                    last_active TIMESTAMP,
                    returned_at TIMESTAMP DEFAULT NULL,
                    message_count INTEGER DEFAULT 0,
                    reaction_count INTEGER DEFAULT 0,
                    voice_minutes REAL DEFAULT 0,
                    qualified_voice_minutes REAL DEFAULT 0,
                    points_total REAL DEFAULT 0,
                    stream_minutes REAL DEFAULT 0,
                    joined_at TIMESTAMP,
                    media_count INTEGER DEFAULT 0,
                    spotify_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)

            # daily_stats: Remembers what happened each day so we can make weekly/monthly charts
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    user_id BIGINT,
                    guild_id BIGINT,
                    channel_id BIGINT DEFAULT 0,
                    date DATE,
                    messages INTEGER DEFAULT 0,
                    reactions INTEGER DEFAULT 0,
                    voice_minutes REAL DEFAULT 0,
                    points REAL DEFAULT 0,
                    stream_minutes REAL DEFAULT 0,
                    game_minutes REAL DEFAULT 0,
                    media_count INTEGER DEFAULT 0,
                    spotify_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, channel_id, date)
                )
            """)

            # daily_game_stats: Tracks time per specific game per day
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_game_stats (
                    user_id BIGINT,
                    guild_id BIGINT,
                    game_name TEXT,
                    date DATE,
                    minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, game_name, date)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS role_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guild_id BIGINT,
                    role_name TEXT,
                    action TEXT,
                    timestamp TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS game_activity (
                    user_id BIGINT,
                    guild_id BIGINT,
                    role_name TEXT,
                    last_played TIMESTAMP,
                    total_minutes REAL DEFAULT 0,
                    bot_assigned INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, role_name)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guild_id BIGINT,
                    channel_id BIGINT,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_minutes REAL,
                    stream_detail TEXT
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reaction_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    target_user_id BIGINT,
                    guild_id BIGINT,
                    channel_id BIGINT,
                    message_id BIGINT,
                    emoji TEXT,
                    timestamp TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS membership_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guild_id BIGINT,
                    action TEXT,
                    timestamp TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_voice_sessions (
                    user_id BIGINT,
                    guild_id BIGINT,
                    channel_id BIGINT,
                    joined_at TIMESTAMP,
                    multiplier REAL,
                    is_streaming INTEGER DEFAULT 0,
                    stream_name TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS active_game_sessions (
                    user_id BIGINT,
                    guild_id BIGINT,
                    game_name TEXT,
                    started_at TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id, game_name)
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS elite_history (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    guild_id BIGINT,
                    category TEXT,
                    win_date DATE
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_overlaps (
                    user_id1 BIGINT,
                    user_id2 BIGINT,
                    guild_id BIGINT,
                    date DATE,
                    overlap_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id1, user_id2, guild_id, date)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_games (
                    guild_id BIGINT,
                    game_substring TEXT,
                    role_suffix TEXT,
                    PRIMARY KEY (guild_id, game_substring)
                )
            """)
            
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS reaction_role_messages (
                    guild_id BIGINT,
                    identifier TEXT,
                    channel_id BIGINT,
                    message_id BIGINT,
                    PRIMARY KEY (guild_id, identifier)
                )
            """)

            # --- MESSAGE ARCHIVE TABLES ---
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

    # --- SETTINGS MGMT ---
    async def get_guild_settings(self, guild_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT settings FROM guild_settings WHERE guild_id = $1", guild_id)
            return row['settings'] if row else {}

    async def update_guild_settings(self, guild_id, settings):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO guild_settings (guild_id, settings) VALUES ($1, $2)
                ON CONFLICT (guild_id) DO UPDATE SET settings = EXCLUDED.settings
            """, guild_id, settings)

    # --- ACTIVITY TRACKING ---
    async def update_activity(self, user_id, guild_id):
        now = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc))
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_activity (user_id, guild_id, last_active) VALUES ($1, $2, $3)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET last_active = EXCLUDED.last_active
            """, user_id, guild_id, now)

    async def set_returned_at(self, user_id, guild_id, timestamp):
        timestamp = _to_naive_utc(timestamp)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_activity SET returned_at = $1 
                WHERE user_id = $2 AND guild_id = $3
            """, timestamp, user_id, guild_id)

    async def increment_messages(self, user_id, guild_id, channel_id, points=1):
        today = datetime.date.today()
        async with self.pool.acquire() as conn:
            # Total
            await conn.execute("""
                UPDATE user_activity SET 
                    message_count = message_count + 1,
                    points_total = points_total + $1
                WHERE user_id = $2 AND guild_id = $3
            """, points, user_id, guild_id)
            # Daily
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, messages, points) VALUES ($1, $2, $3, $4, 1, $5)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    messages = daily_stats.messages + 1,
                    points = daily_stats.points + $6
            """, user_id, guild_id, channel_id, today, points, points)

    async def increment_reactions(self, user_id, guild_id, channel_id, points=1):
        today = datetime.date.today()
        async with self.pool.acquire() as conn:
            # Total
            await conn.execute("""
                UPDATE user_activity SET 
                    reaction_count = reaction_count + 1,
                    points_total = points_total + $1
                WHERE user_id = $2 AND guild_id = $3
            """, points, user_id, guild_id)
            # Daily
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, reactions, points) VALUES ($1, $2, $3, $4, 1, $5)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    reactions = daily_stats.reactions + 1,
                    points = daily_stats.points + $6
            """, user_id, guild_id, channel_id, today, points, points)

    async def increment_media(self, user_id, guild_id, channel_id=0, points=5):
        today = datetime.date.today()
        async with self.pool.acquire() as conn:
            # Total
            await conn.execute("""
                UPDATE user_activity SET 
                    media_count = media_count + 1,
                    points_total = points_total + $1
                WHERE user_id = $2 AND guild_id = $3
            """, points, user_id, guild_id)
            # Daily
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, media_count, points) VALUES ($1, $2, $3, $4, 1, $5)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    media_count = daily_stats.media_count + 1,
                    points = daily_stats.points + $6
            """, user_id, guild_id, channel_id, today, points, points)

    async def add_spotify_minutes(self, user_id, guild_id, minutes):
        today = datetime.date.today()
        async with self.pool.acquire() as conn:
            # Total
            await conn.execute("""
                UPDATE user_activity SET spotify_minutes = spotify_minutes + $1
                WHERE user_id = $2 AND guild_id = $3
            """, minutes, user_id, guild_id)
            # Daily
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, spotify_minutes) VALUES ($1, $2, 0, $3, $4)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    spotify_minutes = daily_stats.spotify_minutes + $5
            """, user_id, guild_id, today, minutes, minutes)

    async def add_voice_minutes(self, user_id, guild_id, channel_id, minutes, multiplier=None, is_streaming=False, is_qualified=False):
        today = datetime.date.today()
        rate = multiplier if multiplier is not None else Config.POINTS_VOICE
        points = minutes * rate
        stream_inc = minutes if is_streaming else 0
        qualified_inc = minutes if is_qualified else 0
        
        async with self.pool.acquire() as conn:
            # Total
            await conn.execute("""
                UPDATE user_activity SET 
                    voice_minutes = voice_minutes + $1,
                    qualified_voice_minutes = qualified_voice_minutes + $2,
                    points_total = points_total + $3,
                    stream_minutes = stream_minutes + $4
                WHERE user_id = $5 AND guild_id = $6
            """, minutes, qualified_inc, points, stream_inc, user_id, guild_id)
            # Daily
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, voice_minutes, points, stream_minutes) VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    voice_minutes = daily_stats.voice_minutes + $8,
                    points = daily_stats.points + $9,
                    stream_minutes = daily_stats.stream_minutes + $10
            """, user_id, guild_id, channel_id, today, minutes, points, stream_inc, minutes, points, stream_inc)

    # --- RETRIEVAL & LEADERBOARDS ---
    async def get_user_data(self, user_id, guild_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM user_activity WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
            return dict(row) if row else None

    async def get_user_daily_activity(self, user_id, guild_id, days=7):
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT date, SUM(points) as points, SUM(voice_minutes) as voice 
                FROM daily_stats 
                WHERE user_id = $1 AND guild_id = $2 AND date >= $3
                GROUP BY date ORDER BY date ASC
            """, user_id, guild_id, cutoff_date)
            return rows

    async def get_user_join_date(self, user_id, guild_id):
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("SELECT joined_at FROM user_activity WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
            return val

    async def update_join_date(self, user_id, guild_id, joined_at):
        joined_at = _to_naive_utc(joined_at)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                UPDATE user_activity SET joined_at = $1 
                WHERE user_id = $2 AND guild_id = $3
            """, joined_at, user_id, guild_id)

    async def get_user_rank(self, user_id, guild_id, days=None):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                val = await conn.fetchval("""
                    WITH period_points AS (
                        SELECT user_id, SUM(points) as total_points 
                        FROM daily_stats 
                        WHERE guild_id = $1 AND date >= $2
                        GROUP BY user_id
                    )
                    SELECT rank FROM (
                        SELECT user_id, RANK() OVER (ORDER BY total_points DESC) as rank 
                        FROM period_points
                    ) s WHERE user_id = $3
                """, guild_id, cutoff, user_id)
            else:
                val = await conn.fetchval("""
                    SELECT rank FROM (
                        SELECT user_id, RANK() OVER (ORDER BY points_total DESC) as rank 
                        FROM user_activity WHERE guild_id = $1
                    ) s WHERE user_id = $2
                """, guild_id, user_id)
            return val

    async def get_leaderboard_data(self, guild_id, days=None, limit=20):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT user_id, SUM(messages) as messages, SUM(reactions) as reactions, 
                           SUM(voice_minutes) as voice, SUM(points) as points, 
                           SUM(stream_minutes) as stream, SUM(media_count) as media
                    FROM daily_stats 
                    WHERE guild_id = $1 AND date >= $2
                    GROUP BY user_id ORDER BY points DESC LIMIT $3
                """, guild_id, cutoff, limit)
            else:
                rows = await conn.fetch("""
                    SELECT user_id, message_count as messages, reaction_count as reactions, 
                           voice_minutes as voice, points_total as points, 
                           stream_minutes as stream, media_count as media
                    FROM user_activity 
                    WHERE guild_id = $1 ORDER BY points_total DESC LIMIT $2
                """, guild_id, limit)
            
            return {r['user_id']: dict(r) for r in rows}

    async def log_membership_event(self, user_id, guild_id, action, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp = _to_naive_utc(timestamp)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO membership_history (user_id, guild_id, action, timestamp) 
                VALUES ($1, $2, $3, $4)
            """, user_id, guild_id, action, timestamp)

    # --- ROLES ---
    async def log_role(self, user_id, guild_id, role_name, action='ADDED', timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        timestamp = _to_naive_utc(timestamp)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO role_history (user_id, guild_id, role_name, action, timestamp) 
                VALUES ($1, $2, $3, $4, $5)
            """, user_id, guild_id, role_name, action, timestamp)

    async def get_role_history(self, guild_id, limit=300):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, role_name, action, timestamp FROM role_history 
                WHERE guild_id = $1 ORDER BY timestamp DESC LIMIT $2
            """, guild_id, limit)
            return rows

    # --- VOICE SESSIONS ---
    async def start_voice_session(self, user_id, guild_id, channel_id, joined_at, multiplier, is_streaming, stream_name):
        joined_at = _to_naive_utc(joined_at)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO active_voice_sessions (user_id, guild_id, channel_id, joined_at, multiplier, is_streaming, stream_name)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET 
                    channel_id = EXCLUDED.channel_id,
                    joined_at = EXCLUDED.joined_at,
                    multiplier = EXCLUDED.multiplier,
                    is_streaming = EXCLUDED.is_streaming,
                    stream_name = EXCLUDED.stream_name
            """, user_id, guild_id, channel_id, joined_at, multiplier, 1 if is_streaming else 0, stream_name)

    async def end_voice_session(self, user_id, guild_id):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM active_voice_sessions WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
            if row:
                await conn.execute("DELETE FROM active_voice_sessions WHERE user_id = $1 AND guild_id = $2", user_id, guild_id)
                return dict(row)
            return None

    async def get_active_voice_sessions(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM active_voice_sessions")
            return {r['user_id']: dict(r) for r in rows}

    async def log_voice_session(self, user_id, guild_id, channel_id, start_time, end_time, duration, stream_detail=None):
        start_time = _to_naive_utc(start_time)
        end_time = _to_naive_utc(end_time)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration_minutes, stream_detail)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, guild_id, channel_id, start_time, end_time, duration, stream_detail)

    async def get_voice_overlaps(self, user_id, guild_id, limit=10):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id2 as target_id, SUM(overlap_minutes) as total 
                FROM voice_overlaps 
                WHERE user_id1 = $1 AND guild_id = $2
                GROUP BY user_id2 ORDER BY total DESC LIMIT $3
            """, user_id, guild_id, limit)
            return rows

    async def add_voice_overlap(self, u1, u2, guild_id, minutes):
        today = datetime.date.today()
        # Sort so we always store (smaller_id, larger_id) to avoid duplicates
        p1, p2 = min(u1, u2), max(u1, u2)
        async with self.pool.acquire() as conn:
            # We insert twice for easy querying (A-B and B-A)
            for pair in [(p1, p2), (p2, p1)]:
                await conn.execute("""
                    INSERT INTO voice_overlaps (user_id1, user_id2, guild_id, date, overlap_minutes)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT(user_id1, user_id2, guild_id, date) DO UPDATE SET 
                        overlap_minutes = voice_overlaps.overlap_minutes + $6
                """, pair[0], pair[1], guild_id, today, minutes, minutes)

    # --- GAME PERSISTENCE ---
    async def start_game_session(self, user_id, guild_id, game_name, started_at):
        started_at = _to_naive_utc(started_at)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO active_game_sessions (user_id, guild_id, game_name, started_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT(user_id, guild_id, game_name) DO UPDATE SET started_at = EXCLUDED.started_at
            """, user_id, guild_id, game_name, started_at)

    async def end_game_session(self, user_id, guild_id, game_name):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT started_at FROM active_game_sessions WHERE user_id = $1 AND guild_id = $2 AND game_name = $3", user_id, guild_id, game_name)
            if row:
                await conn.execute("DELETE FROM active_game_sessions WHERE user_id = $1 AND guild_id = $2 AND game_name = $3", user_id, guild_id, game_name)
                return row['started_at']
            return None

    async def get_active_game_sessions(self):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id, guild_id, game_name, started_at FROM active_game_sessions")
            return {(r['user_id'], r['guild_id'], r['game_name']): r['started_at'] for r in rows}

    async def add_game_minutes(self, user_id, guild_id, game_name, minutes):
        today = datetime.date.today()
        async with self.pool.acquire() as conn:
            # 1. Total (per game)
            await conn.execute("""
                UPDATE game_activity SET total_minutes = total_minutes + $1 
                WHERE user_id = $2 AND guild_id = $3 AND role_name = $4
            """, minutes, user_id, guild_id, game_name)
            
            # 2. Daily Summary
            await conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, game_minutes) VALUES ($1, $2, 0, $3, $4)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    game_minutes = daily_stats.game_minutes + $5
            """, user_id, guild_id, today, minutes, minutes)
            
            # 3. Daily Per-Game
            await conn.execute("""
                INSERT INTO daily_game_stats (user_id, guild_id, game_name, date, minutes) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT(user_id, guild_id, game_name, date) DO UPDATE SET 
                    minutes = daily_game_stats.minutes + $6
            """, user_id, guild_id, game_name, today, minutes, minutes)

    async def get_game_stats_report(self, guild_id, timeframe="alltime"):
        async with self.pool.acquire() as conn:
            if timeframe == "monthly":
                cutoff = datetime.date.today() - datetime.timedelta(days=30)
                rows = await conn.fetch("""
                    SELECT game_name as display_name, COUNT(DISTINCT user_id) as user_count, SUM(minutes) as total_minutes 
                    FROM daily_game_stats WHERE guild_id = $1 AND date >= $2
                    GROUP BY game_name ORDER BY total_minutes DESC
                """, guild_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT role_name as display_name, COUNT(DISTINCT user_id) as user_count, SUM(total_minutes) as total_minutes 
                    FROM game_activity WHERE guild_id = $1
                    GROUP BY role_name ORDER BY total_minutes DESC
                """, guild_id)
            return rows

    # --- TRACKED GAMES ---
    async def get_tracked_games(self, guild_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT game_substring, role_suffix FROM tracked_games WHERE guild_id = $1", guild_id)
            return {r['game_substring']: r['role_suffix'] for r in rows}

    async def add_tracked_game(self, guild_id, substring, suffix):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO tracked_games (guild_id, game_substring, role_suffix) VALUES ($1, $2, $3)
                ON CONFLICT(guild_id, game_substring) DO UPDATE SET role_suffix = EXCLUDED.role_suffix
            """, guild_id, substring, suffix)

    async def remove_tracked_game(self, guild_id, substring):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM tracked_games WHERE guild_id = $1 AND game_substring = $2", guild_id, substring)

    # --- INTERACTIONS & REACTION ROLE MESSAGES ---
    async def log_reaction_interaction(self, user_id, target_user_id, guild_id, channel_id, message_id, emoji):
        now = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc))
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO reaction_history (user_id, target_user_id, guild_id, channel_id, message_id, emoji, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, user_id, target_user_id, guild_id, channel_id, message_id, emoji, now)

    async def get_reaction_role_message(self, guild_id, identifier):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("SELECT channel_id, message_id FROM reaction_role_messages WHERE guild_id = $1 AND identifier = $2", guild_id, identifier)
            return (row['channel_id'], row['message_id']) if row else None

    async def save_reaction_role_message(self, guild_id, identifier, channel_id, message_id):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO reaction_role_messages (guild_id, identifier, channel_id, message_id) VALUES ($1, $2, $3, $4)
                ON CONFLICT(guild_id, identifier) DO UPDATE SET channel_id = EXCLUDED.channel_id, message_id = EXCLUDED.message_id
            """, guild_id, identifier, channel_id, message_id)

    # --- ELITE STATS ---
    async def get_weekly_elite_stats(self, guild_id, start_date, end_date):
        async with self.pool.acquire() as conn:
            spotify = await conn.fetch("SELECT user_id, SUM(spotify_minutes) as total FROM daily_stats WHERE guild_id = $1 AND date >= $2 AND date <= $3 GROUP BY user_id ORDER BY total DESC LIMIT 50", guild_id, start_date, end_date)
            game_total = await conn.fetch("SELECT user_id, SUM(game_minutes) as total FROM daily_stats WHERE guild_id = $1 AND date >= $2 AND date <= $3 GROUP BY user_id ORDER BY total DESC LIMIT 50", guild_id, start_date, end_date)
            variety = await conn.fetch(f"SELECT user_id, COUNT(DISTINCT game_name) as variety FROM daily_game_stats WHERE guild_id = $1 AND date >= $2 AND date <= $3 AND minutes >= {Config.VARIETY_MIN_MINUTES} GROUP BY user_id ORDER BY variety DESC LIMIT 50", guild_id, start_date, end_date)
            stream = await conn.fetch("SELECT user_id, SUM(stream_minutes) as total FROM daily_stats WHERE guild_id = $1 AND date >= $2 AND date <= $3 GROUP BY user_id ORDER BY total DESC LIMIT 50", guild_id, start_date, end_date)
            media = await conn.fetch("SELECT user_id, SUM(media_count) as total FROM daily_stats WHERE guild_id = $1 AND date >= $2 AND date <= $3 GROUP BY user_id ORDER BY total DESC LIMIT 50", guild_id, start_date, end_date)
            
            return {
                "spotify": spotify,
                "gamer_total": game_total,
                "gamer_variety": variety,
                "streamer": stream,
                "media": media
            }

    async def log_elite_win(self, user_id, guild_id, category, win_date):
        async with self.pool.acquire() as conn:
            await conn.execute("INSERT INTO elite_history (user_id, guild_id, category, win_date) VALUES ($1, $2, $3, $4)", user_id, guild_id, category, win_date)

    async def get_last_elites(self, guild_id):
        async with self.pool.acquire() as conn:
            # Get winners from the most recent date
            rows = await conn.fetch("""
                WITH last_date AS (SELECT MAX(win_date) FROM elite_history WHERE guild_id = $1)
                SELECT category, user_id FROM elite_history WHERE guild_id = $1 AND win_date = (SELECT * FROM last_date)
            """, guild_id)
            return {r['category']: r['user_id'] for r in rows}

    async def get_last_elites_run_date(self, guild_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchval("SELECT MAX(win_date) FROM elite_history WHERE guild_id = $1", guild_id)

    async def get_elite_wins(self, user_id, guild_id):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT category, COUNT(*) as count FROM elite_history WHERE user_id = $1 AND guild_id = $2 GROUP BY category", user_id, guild_id)
            return {r['category']: r['count'] for r in rows}

    async def get_user_weekly_elite_stats(self, user_id, guild_id, start_date, end_date):
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT SUM(spotify_minutes) as spotify, SUM(game_minutes) as game_total, 
                       SUM(stream_minutes) as streamer, SUM(media_count) as media
                FROM daily_stats WHERE user_id = $1 AND guild_id = $2 AND date >= $3 AND date <= $4
            """, user_id, guild_id, start_date, end_date)
            
            variety = await conn.fetchval(f"SELECT COUNT(DISTINCT game_name) FROM daily_game_stats WHERE user_id = $1 AND guild_id = $2 AND date >= $3 AND date <= $4 AND minutes >= {Config.VARIETY_MIN_MINUTES}", user_id, guild_id, start_date, end_date)
            
            return {
                "spotify": row['spotify'] or 0 if row else 0,
                "gamer_total": row['game_total'] or 0 if row else 0,
                "gamer_variety": variety or 0,
                "streamer": row['streamer'] or 0 if row else 0,
                "media": row['media'] or 0 if row else 0
            }

    async def get_top_voice_partners(self, user_id, guild_id, days=30):
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id2 as partner_id, SUM(overlap_minutes) as overlap
                FROM voice_overlaps 
                WHERE user_id1 = $1 AND guild_id = $2 AND date >= $3
                GROUP BY user_id2 ORDER BY overlap DESC LIMIT 10
            """, user_id, guild_id, cutoff_date)
            return rows

    async def get_top_game_buddies(self, user_id, guild_id, game_name, limit=10):
        async with self.pool.acquire() as conn:
            # Note: This is a complex query to estimate overlap based on daily activity 
            # (simplified: people who played the same game on the same day)
            rows = await conn.fetch("""
                SELECT t2.user_id as partner_id, SUM(LEAST(t1.minutes, t2.minutes)) as common_minutes
                FROM daily_game_stats t1
                JOIN daily_game_stats t2 ON t1.game_name = t2.game_name AND t1.date = t2.date AND t1.guild_id = t2.guild_id
                WHERE t1.user_id = $1 AND t1.guild_id = $2 AND t1.game_name = $3 AND t2.user_id != $1
                GROUP BY t2.user_id ORDER BY common_minutes DESC LIMIT $4
            """, user_id, guild_id, game_name, limit)
            return rows

    async def get_inactive_users(self, guild_id, days):
        cutoff = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, last_active, returned_at FROM user_activity 
                WHERE guild_id = $1 AND last_active < $2
            """, guild_id, cutoff)
            return {r['user_id']: dict(r) for r in rows}

    async def get_user_recent_games(self, user_id, guild_id, limit=3):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT role_name as name, last_played, total_minutes as minutes 
                FROM game_activity 
                WHERE user_id = $1 AND guild_id = $2 
                ORDER BY last_played DESC LIMIT $3
            """, user_id, guild_id, limit)
            return rows

    async def get_user_stats_for_period(self, user_id, guild_id, days):
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT SUM(messages) as messages, SUM(reactions) as reactions, 
                       SUM(voice_minutes) as voice, SUM(points) as points, 
                       SUM(stream_minutes) as stream, SUM(media_count) as media
                FROM daily_stats 
                WHERE user_id = $1 AND guild_id = $2 AND date >= $3
            """, user_id, guild_id, cutoff)
            
            if row and row['points'] is not None:
                return dict(row)
            return {"messages":0, "reactions":0, "voice":0, "points":0, "stream":0, "media":0}

    async def update_game_activity(self, user_id, guild_id, role_name, bot_assigned=False):
        now = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc))
        async with self.pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO game_activity (user_id, guild_id, role_name, last_played, bot_assigned)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT(user_id, guild_id, role_name) DO UPDATE SET 
                    last_played = EXCLUDED.last_played,
                    bot_assigned = EXCLUDED.bot_assigned
            """, user_id, guild_id, role_name, now, 1 if bot_assigned else 0)

    async def get_inactive_games(self, guild_id, days):
        cutoff = _to_naive_utc(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days))
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, role_name FROM game_activity 
                WHERE guild_id = $1 AND last_played < $2 AND bot_assigned = 1
            """, guild_id, cutoff)
            return [(r['user_id'], r['role_name']) for r in rows]

    async def remove_game_activity(self, user_id, guild_id, role_name):
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM game_activity WHERE user_id = $1 AND guild_id = $2 AND role_name = $3", user_id, guild_id, role_name)

    async def get_user_social_stats(self, user_id, guild_id, days=30):
        cutoff = datetime.date.today() - datetime.timedelta(days=days)
        async with self.pool.acquire() as conn:
            # Top emoji
            emoji_row = await conn.fetchrow("""
                SELECT emoji, COUNT(*) as count FROM reaction_history 
                WHERE user_id = $1 AND guild_id = $2 AND timestamp >= $3
                GROUP BY emoji ORDER BY count DESC LIMIT 1
            """, user_id, guild_id, cutoff)
            
            # Most reacted to person
            target_row = await conn.fetchrow("""
                SELECT target_user_id, COUNT(*) as count FROM reaction_history 
                WHERE user_id = $1 AND guild_id = $2 AND timestamp >= $3
                GROUP BY target_user_id ORDER BY count DESC LIMIT 1
            """, user_id, guild_id, cutoff)
            
            return {
                "top_emoji": emoji_row['emoji'] if emoji_row else None,
                "top_target": target_row['target_user_id'] if target_row else None
            }

    async def get_user_top_games(self, user_id, guild_id, limit=3):
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT role_name as name, total_minutes as minutes 
                FROM game_activity 
                WHERE user_id = $1 AND guild_id = $2 
                ORDER BY total_minutes DESC LIMIT $3
            """, user_id, guild_id, limit)
            return rows

    async def get_user_average_voice_duration(self, user_id, guild_id):
        async with self.pool.acquire() as conn:
            val = await conn.fetchval("""
                SELECT AVG(duration_minutes) FROM voice_sessions 
                WHERE user_id = $1 AND guild_id = $2
            """, user_id, guild_id)
            return val or 0

    async def get_peak_activity_raw(self, guild_id, days=None):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT EXTRACT(DOW FROM timestamp) as day, EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count 
                    FROM messages 
                    WHERE guild_id = $1 AND timestamp >= $2
                    GROUP BY day, hour
                """, guild_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT EXTRACT(DOW FROM timestamp) as day, EXTRACT(HOUR FROM timestamp) as hour, COUNT(*) as count 
                    FROM messages 
                    WHERE guild_id = $1
                    GROUP BY day, hour
                """, guild_id)
            return [[r['day'], r['hour'], r['count']] for r in rows]

    async def get_voice_usage_raw(self, guild_id, days=None):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT channel_id, SUM(duration_minutes) as minutes 
                    FROM voice_sessions 
                    WHERE guild_id = $1 AND start_time >= $2
                    GROUP BY channel_id ORDER BY minutes DESC LIMIT 10
                """, guild_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT channel_id, SUM(duration_minutes) as minutes 
                    FROM voice_sessions 
                    WHERE guild_id = $1
                    GROUP BY channel_id ORDER BY minutes DESC LIMIT 10
                """, guild_id)
            return [[r['channel_id'], r['minutes']] for r in rows]

    async def get_top_average_voice_duration(self, guild_id, days=None):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT user_id, AVG(duration_minutes) as avg_mins 
                    FROM voice_sessions 
                    WHERE guild_id = $1 AND start_time >= $2
                    GROUP BY user_id ORDER BY avg_mins DESC LIMIT 10
                """, guild_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT user_id, AVG(duration_minutes) as avg_mins 
                    FROM voice_sessions 
                    WHERE guild_id = $1
                    GROUP BY user_id ORDER BY avg_mins DESC LIMIT 10
                """, guild_id)
            return [[r['user_id'], r['avg_mins']] for r in rows]

    async def get_channel_activity_raw(self, guild_id, days=None):
        async with self.pool.acquire() as conn:
            if days:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = await conn.fetch("""
                    SELECT channel_id, COUNT(*) as total 
                    FROM messages 
                    WHERE guild_id = $1 AND timestamp >= $2
                    GROUP BY channel_id ORDER BY total DESC LIMIT 10
                """, guild_id, cutoff)
            else:
                rows = await conn.fetch("""
                    SELECT channel_id, COUNT(*) as total 
                    FROM messages 
                    WHERE guild_id = $1
                    GROUP BY channel_id ORDER BY total DESC LIMIT 10
                """, guild_id)
            return [[r['channel_id'], r['total']] for r in rows]








