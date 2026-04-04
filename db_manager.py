import sqlite3
import datetime
from config_loader import Config

class DBManager:
    def __init__(self, db_path="activity.db"):
        # Tell the bot where the database file is and set up the tables
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        # This function creates the 'drawers' (tables) in our database if they don't exist yet
        with self._get_connection() as conn:
            # user_activity: Stores the overall numbers for each person (messages, voice time, etc.)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
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
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            # daily_stats: Remembers what happened each day so we can make weekly/monthly charts
            # Updated to track per-channel activity!
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    user_id INTEGER,
                    guild_id INTEGER,
                    channel_id INTEGER DEFAULT 0,
                    date DATE,
                    messages INTEGER DEFAULT 0,
                    reactions INTEGER DEFAULT 0,
                    voice_minutes REAL DEFAULT 0,
                    points REAL DEFAULT 0,
                    stream_minutes REAL DEFAULT 0,
                    media_count INTEGER DEFAULT 0,
                    game_minutes REAL DEFAULT 0,
                    spotify_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, channel_id, date)
                )
            """)
            # daily_game_stats: Tracks how much each game is played per day for variety awards
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_game_stats (
                    user_id INTEGER,
                    guild_id INTEGER,
                    game_name TEXT,
                    date DATE,
                    minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, game_name, date)
                )
            """)
            # role_history: A log of when the bot gave or took away a role from someone
            conn.execute("""
                CREATE TABLE IF NOT EXISTS role_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    role_name TEXT,
                    action TEXT DEFAULT 'ADDED',
                    timestamp TIMESTAMP
                )
            """)
            # game_activity: Keeps track of how much time people spend playing specific games
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
                    role_name TEXT,
                    last_played TIMESTAMP,
                    total_minutes REAL DEFAULT 0,
                    bot_assigned INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, role_name)
                )
            """)
            # voice_sessions: Records every time someone joins and leaves a voice channel
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_minutes REAL,
                    stream_detail TEXT
                )
            """)
            # reaction_history: Remembers who gave a reaction to which message
            conn.execute("""
                CREATE TABLE IF NOT EXISTS reaction_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    target_user_id INTEGER,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    message_id INTEGER,
                    emoji TEXT,
                    timestamp TIMESTAMP
                )
            """)
            # membership_history: Logs every join and leave event
            conn.execute("""
                CREATE TABLE IF NOT EXISTS membership_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    action TEXT, -- 'JOIN' or 'LEAVE'
                    timestamp TIMESTAMP
                )
            """)
            # tracked_games: A list of games the bot is currently looking for to give out roles
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_games (
                    game_substring TEXT PRIMARY KEY,
                    role_suffix TEXT
                )
            """)
            # active_voice_sessions: Remembers who is currently in a voice channel
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_voice_sessions (
                    user_id INTEGER,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    joined_at TIMESTAMP,
                    multiplier REAL DEFAULT 2.0,
                    is_streaming INTEGER DEFAULT 0,
                    stream_name TEXT,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            
            # Migrations for active_voice_sessions
            for col, ctype in [("multiplier", "REAL DEFAULT 2.0"), ("is_streaming", "INTEGER DEFAULT 0"), ("stream_name", "TEXT")]:
                try: conn.execute(f"ALTER TABLE active_voice_sessions ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError: pass
            # active_game_sessions: Remembers who is currently playing a game
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_game_sessions (
                    user_id INTEGER,
                    guild_id INTEGER,
                    game_name TEXT,
                    started_at TIMESTAMP,
                    PRIMARY KEY (user_id, guild_id, game_name)
                )
            """)
            # champion_history: Logs weekly champions for role management and log display
            conn.execute("""
                CREATE TABLE IF NOT EXISTS champion_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    category TEXT,
                    win_date DATE
                )
            """)
            
            # Migrations for user_activity
            for col, ctype in [("returned_at", "TIMESTAMP DEFAULT NULL"), ("message_count", "INTEGER DEFAULT 0"), 
                               ("reaction_count", "INTEGER DEFAULT 0"), ("voice_minutes", "REAL DEFAULT 0"),
                               ("qualified_voice_minutes", "REAL DEFAULT 0")]:
                try: conn.execute(f"ALTER TABLE user_activity ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError: pass
            
            # Migrations for role_history
            try: conn.execute("ALTER TABLE role_history ADD COLUMN action TEXT DEFAULT 'ADDED'")
            except sqlite3.OperationalError: pass

            # Migrations for game_activity
            try: conn.execute("ALTER TABLE game_activity ADD COLUMN total_minutes REAL DEFAULT 0")
            except sqlite3.OperationalError: pass
            
            # Migration for daily_stats (Add channel_id and update Primary Key)
            # Check if channel_id already exists
            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            cols = [row[1] for row in cursor.fetchall()]
            if "channel_id" not in cols:
                try:
                    # Rename old, create new, copy data
                    conn.execute("ALTER TABLE daily_stats RENAME TO daily_stats_old")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS daily_stats (
                            user_id INTEGER,
                            guild_id INTEGER,
                            channel_id INTEGER DEFAULT 0,
                            date DATE,
                            messages INTEGER DEFAULT 0,
                            reactions INTEGER DEFAULT 0,
                            voice_minutes REAL DEFAULT 0,
                            PRIMARY KEY (user_id, guild_id, channel_id, date)
                        )
                    """)
                    conn.execute("""
                        INSERT INTO daily_stats (user_id, guild_id, channel_id, date, messages, reactions, voice_minutes)
                        SELECT user_id, guild_id, 0, date, messages, reactions, voice_minutes FROM daily_stats_old
                    """)
                    conn.execute("DROP TABLE daily_stats_old")
                except sqlite3.OperationalError as e:
                    print(f"Migration error: {e}")
            
            # Migration to add points columns if they don't exist
            # 1. user_activity points_total
            cursor = conn.execute("PRAGMA table_info(user_activity)")
            if "points_total" not in [row[1] for row in cursor.fetchall()]:
                try: 
                    conn.execute("ALTER TABLE user_activity ADD COLUMN points_total REAL DEFAULT 0")
                    # Initialize based on old formula: msg*10 + reac*5 + voice*2
                    conn.execute("UPDATE user_activity SET points_total = (message_count * 10) + (reaction_count * 5) + (voice_minutes * 2)")
                except sqlite3.OperationalError: pass
                
            # 2. daily_stats points
            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            if "points" not in [row[1] for row in cursor.fetchall()]:
                try: 
                    conn.execute("ALTER TABLE daily_stats ADD COLUMN points REAL DEFAULT 0")
                    # Initialize based on old formula
                    conn.execute("UPDATE daily_stats SET points = (messages * 10) + (reactions * 5) + (voice_minutes * 2)")
                except sqlite3.OperationalError: pass
            
            # Migration for stream_minutes
            cursor = conn.execute("PRAGMA table_info(user_activity)")
            if "stream_minutes" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE user_activity ADD COLUMN stream_minutes REAL DEFAULT 0")
                except sqlite3.OperationalError: pass
                
            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            if "stream_minutes" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE daily_stats ADD COLUMN stream_minutes REAL DEFAULT 0")
                except sqlite3.OperationalError: pass
            
            # Migration for voice_sessions stream_detail
            cursor = conn.execute("PRAGMA table_info(voice_sessions)")
            if "stream_detail" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE voice_sessions ADD COLUMN stream_detail TEXT")
                except sqlite3.OperationalError: pass
            
            # Migration for daily_stats game_minutes
            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            if "game_minutes" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE daily_stats ADD COLUMN game_minutes REAL DEFAULT 0")
                except sqlite3.OperationalError: pass
                
            # Migration for joined_at in user_activity
            cursor = conn.execute("PRAGMA table_info(user_activity)")
            if "joined_at" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE user_activity ADD COLUMN joined_at TIMESTAMP")
                except sqlite3.OperationalError: pass
                
            # Migration for media_count
            cursor = conn.execute("PRAGMA table_info(user_activity)")
            if "media_count" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE user_activity ADD COLUMN media_count INTEGER DEFAULT 0")
                except sqlite3.OperationalError: pass
            
            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            if "media_count" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE daily_stats ADD COLUMN media_count INTEGER DEFAULT 0")
                except sqlite3.OperationalError: pass
            
            # Migration for spotify_minutes
            cursor = conn.execute("PRAGMA table_info(user_activity)")
            if "spotify_minutes" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE user_activity ADD COLUMN spotify_minutes REAL DEFAULT 0")
                except sqlite3.OperationalError: pass

            cursor = conn.execute("PRAGMA table_info(daily_stats)")
            if "spotify_minutes" not in [row[1] for row in cursor.fetchall()]:
                try: conn.execute("ALTER TABLE daily_stats ADD COLUMN spotify_minutes REAL DEFAULT 0")
                except sqlite3.OperationalError: pass
            # --- INDEXES FOR PERFORMANCE ---
            
            # user_activity: guild_id for server-wide lookups
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_activity_guild ON user_activity(guild_id)")
            
            # daily_stats: guild_id+date (leaderboard) and user+guild+date (individual stats)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_guild_date ON daily_stats(guild_id, date)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_daily_stats_user_guild_date ON daily_stats(user_id, guild_id, date)")
            
            # voice_sessions: user+guild for profile lookups, start_time for history
            conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_sessions_user_guild ON voice_sessions(user_id, guild_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_sessions_start ON voice_sessions(start_time)")
            
            # reaction_history: user+guild and timestamp for social metrics
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reaction_history_user_guild ON reaction_history(user_id, guild_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_reaction_history_time ON reaction_history(timestamp)")
            
            # role_history: user+guild and timestamp for audit logs
            conn.execute("CREATE INDEX IF NOT EXISTS idx_role_history_user_guild ON role_history(user_id, guild_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_role_history_time ON role_history(timestamp)")
            
            # membership_history: user+guild and timestamp for event tracking
            conn.execute("CREATE INDEX IF NOT EXISTS idx_membership_history_user_guild ON membership_history(user_id, guild_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_membership_history_time ON membership_history(timestamp)")
            
            # game_activity: user+guild for profile game-time lookup
            conn.execute("CREATE INDEX IF NOT EXISTS idx_game_activity_user_guild ON game_activity(user_id, guild_id)")

            # --- VOICE OVERLAPS CACHE ---
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_overlaps (
                    user_id1 INTEGER,
                    user_id2 INTEGER,
                    guild_id INTEGER,
                    date DATE,
                    overlap_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id1, user_id2, guild_id, date)
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_overlaps_u1_g ON voice_overlaps(user_id1, guild_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_overlaps_u2_g ON voice_overlaps(user_id2, guild_id)")

            conn.commit()

    def update_activity(self, user_id, guild_id, last_active=None):
        # Update the 'last seen' time for a user so we know they are still around
        if last_active is None:
            last_active = datetime.datetime.now(datetime.timezone.utc)
        
        last_active_str = last_active.isoformat()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO user_activity (user_id, guild_id, last_active)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET last_active = excluded.last_active
            """, (user_id, guild_id, last_active_str))
            conn.commit()

    def set_returned_at(self, user_id, guild_id, timestamp=None):
        # Sets when the user came back after being away for a long time
        timestamp_str = timestamp.isoformat() if timestamp else None
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE user_activity SET returned_at = ? WHERE user_id = ? AND guild_id = ?
            """, (timestamp_str, user_id, guild_id))
            conn.commit()

    def increment_messages(self, user_id, guild_id, channel_id=0, points=10):
        # Add 1 to the message count for a user (both total and for today)
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("""
                UPDATE user_activity SET 
                    message_count = message_count + 1,
                    points_total = points_total + ?
                WHERE user_id = ? AND guild_id = ?
            """, (points, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, messages, points) VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    messages = messages + 1,
                    points = points + ?
            """, (user_id, guild_id, channel_id, today, points, points))
            conn.commit()

    def increment_reactions(self, user_id, guild_id, channel_id=0, points=5):
        # Add 1 to the reaction count for a user (both total and for today)
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("""
                UPDATE user_activity SET 
                    reaction_count = reaction_count + 1,
                    points_total = points_total + ?
                WHERE user_id = ? AND guild_id = ?
            """, (points, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, reactions, points) VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    reactions = reactions + 1,
                    points = points + ?
            """, (user_id, guild_id, channel_id, today, points, points))
            conn.commit()

    def increment_media(self, user_id, guild_id, channel_id=0, points=5):
        # Add 1 to the media count for a user (both total and for today)
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("""
                UPDATE user_activity SET 
                    media_count = media_count + 1,
                    points_total = points_total + ?
                WHERE user_id = ? AND guild_id = ?
            """, (points, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, media_count, points) VALUES (?, ?, ?, ?, 1, ?)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    media_count = media_count + 1,
                    points = points + ?
            """, (user_id, guild_id, channel_id, today, points, points))
            conn.commit()

    def add_spotify_minutes(self, user_id, guild_id, minutes):
        # We don't give points for Spotify, it's just for the SpotiVibe role
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("""
                UPDATE user_activity SET spotify_minutes = spotify_minutes + ?
                WHERE user_id = ? AND guild_id = ?
            """, (minutes, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, spotify_minutes) VALUES (?, ?, 0, ?, ?)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    spotify_minutes = spotify_minutes + ?
            """, (user_id, guild_id, today, minutes, minutes))
            conn.commit()

    def add_voice_minutes(self, user_id, guild_id, channel_id, minutes, multiplier=None, is_streaming=False, is_qualified=False):
        # Add the minutes someone spent in voice to their stats
        today = datetime.date.today()
        # Use provided multiplier or fall back to config
        rate = multiplier if multiplier is not None else Config.POINTS_VOICE
        points = minutes * rate
        stream_inc = minutes if is_streaming else 0
        qualified_inc = minutes if is_qualified else 0
        
        with self._get_connection() as conn:
            # Total
            conn.execute("""
                UPDATE user_activity SET 
                    voice_minutes = voice_minutes + ?,
                    qualified_voice_minutes = qualified_voice_minutes + ?,
                    points_total = points_total + ?,
                    stream_minutes = stream_minutes + ?
                WHERE user_id = ? AND guild_id = ?
            """, (minutes, qualified_inc, points, stream_inc, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, channel_id, date, voice_minutes, points, stream_minutes) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id, channel_id, date) DO UPDATE SET 
                    voice_minutes = voice_minutes + ?,
                    points = points + ?,
                    stream_minutes = stream_minutes + ?
            """, (user_id, guild_id, channel_id, today, minutes, points, stream_inc, minutes, points, stream_inc))
            conn.commit()

    def get_leaderboard_data(self, guild_id, days=None, limit=None):
        # Get the top players for the leaderboard (last X days or all-time)
        limit_clause = f" LIMIT {limit}" if limit else ""
        with self._get_connection() as conn:
            if days:
                cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
                query = f"""
                    SELECT user_id, SUM(messages), SUM(reactions), SUM(voice_minutes), SUM(points), SUM(stream_minutes), SUM(media_count)
                    FROM daily_stats WHERE guild_id = ? AND date >= ? 
                    GROUP BY user_id ORDER BY SUM(points) DESC{limit_clause}
                """
                cursor = conn.execute(query, (int(guild_id), cutoff_date))
            else:
                query = f"""
                    SELECT user_id, message_count, reaction_count, voice_minutes, points_total, stream_minutes, media_count
                    FROM user_activity WHERE guild_id = ? ORDER BY points_total DESC{limit_clause}
                """
                cursor = conn.execute(query, (int(guild_id),))
            
            rows = cursor.fetchall()
            # Note: We now return 7 values per user to include streaming and media
            return {row[0]: {
                "messages": row[1] or 0, 
                "reactions": row[2] or 0, 
                "voice": row[3] or 0, 
                "points": row[4] or 0,
                "stream": row[5] or 0,
                "media": row[6] or 0
            } for row in rows}

    def get_user_data(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT last_active, returned_at, message_count, reaction_count, voice_minutes, media_count, spotify_minutes, points_total, stream_minutes, qualified_voice_minutes
                FROM user_activity WHERE user_id = ? AND guild_id = ?
            """, (int(user_id), int(guild_id)))
            row = cursor.fetchone()
            if row:
                last_active = datetime.datetime.fromisoformat(row[0])
                returned_at = datetime.datetime.fromisoformat(row[1]) if row[1] else None
                return {
                    "last_active": last_active, 
                    "returned_at": returned_at,
                    "message_count": row[2],
                    "reaction_count": row[3],
                    "voice_minutes": row[4],
                    "media_count": row[5],
                    "spotify_minutes": row[6],
                    "points_total": row[7],
                    "stream_minutes": row[8],
                    "qualified_voice_minutes": row[9]
                }
            return None

    def get_user_daily_points(self, user_id, guild_id, days=7):
        """Fetches daily point totals for a user for the last X days, filling gaps with 0."""
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days-1)
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT date, SUM(points) as daily_points 
                FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ?
                GROUP BY date ORDER BY date ASC
            """, (int(user_id), int(guild_id), cutoff_date.isoformat()))
            
            rows = cursor.fetchall()
            
            # Create a dictionary with all dates in the range, default 0 points
            result = {}
            for i in range(days):
                d = cutoff_date + datetime.timedelta(days=i)
                result[d.isoformat()] = 0
            
            # Update with actual data from DB
            for date_str, points in rows:
                result[date_str] = points or 0
            
            # Return as sorted list of tuples (date_str, points)
            return sorted(list(result.items()))

    def get_user_daily_activity(self, user_id, guild_id, days=7):
        """Fetches daily point totals and voice minutes for a user for the last X days, filling gaps with 0."""
        cutoff_date = datetime.date.today() - datetime.timedelta(days=days-1)
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT date, SUM(points) as daily_points, SUM(voice_minutes) as daily_voice
                FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ?
                GROUP BY date ORDER BY date ASC
            """, (int(user_id), int(guild_id), cutoff_date.isoformat()))
            
            rows = cursor.fetchall()
            
            # Create a dictionary with all dates in the range, default 0
            result = {}
            for i in range(days):
                d = cutoff_date + datetime.timedelta(days=i)
                result[d.isoformat()] = {"points": 0, "voice": 0}
            
            # Update with actual data from DB
            for date_str, points, voice in rows:
                result[date_str] = {"points": points or 0, "voice": voice or 0}
            
            # Return as sorted list of tuples (date_str, points, voice)
            return [(d, r["points"], r["voice"]) for d, r in sorted(result.items())]

    def get_all_guild_data(self, guild_id):
        # [DEPRECATED] Use get_inactive_users or specific queries instead
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, last_active, returned_at, message_count, reaction_count, voice_minutes, media_count, spotify_minutes, points_total, stream_minutes
                FROM user_activity WHERE guild_id = ?
            """, (int(guild_id),))
            rows = cursor.fetchall()
            data = {}
            for row in rows:
                data[row[0]] = {
                    "last_active": datetime.datetime.fromisoformat(row[1]),
                    "returned_at": datetime.datetime.fromisoformat(row[2]) if row[2] else None,
                    "message_count": row[3],
                    "reaction_count": row[4],
                    "voice_minutes": row[5],
                    "media_count": row[6],
                    "spotify_minutes": row[7],
                    "points_total": row[8],
                    "stream_minutes": row[9]
                }
            return data

    def get_inactive_users(self, guild_id, threshold_days):
        """Fetches only users who are inactive based on the threshold, for more efficient processing."""
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=threshold_days)
        cutoff_str = cutoff_date.isoformat()
        
        with self._get_connection() as conn:
            # We fetch those whose last_active is old OR they have a returned_at (grace period check)
            cursor = conn.execute("""
                SELECT user_id, last_active, returned_at FROM user_activity 
                WHERE guild_id = ? AND (last_active < ? OR returned_at IS NOT NULL)
            """, (int(guild_id), cutoff_str))
            
            rows = cursor.fetchall()
            return {row[0]: {
                "last_active": datetime.datetime.fromisoformat(row[1]),
                "returned_at": datetime.datetime.fromisoformat(row[2]) if row[2] else None
            } for row in rows}

    def get_user_rank(self, user_id, guild_id, days=None):
        """Calculates a user's rank compared to others in the server efficiently."""
        with self._get_connection() as conn:
            if days:
                cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
                # 1. Get user's points for the period
                cursor = conn.execute("""
                    SELECT SUM(points) FROM daily_stats 
                    WHERE user_id = ? AND guild_id = ? AND date >= ?
                """, (int(user_id), int(guild_id), cutoff_date))
                user_points = cursor.fetchone()[0] or 0
                
                # 2. Count users with more points
                cursor = conn.execute("""
                    SELECT COUNT(*) + 1 FROM (
                        SELECT user_id, SUM(points) as total_pts FROM daily_stats 
                        WHERE guild_id = ? AND date >= ? 
                        GROUP BY user_id HAVING total_pts > ?
                    )
                """, (int(guild_id), cutoff_date, user_points))
                return cursor.fetchone()[0]
            else:
                # 1. Get user's total points
                cursor = conn.execute("SELECT points_total FROM user_activity WHERE user_id = ? AND guild_id = ?", (int(user_id), int(guild_id)))
                row = cursor.fetchone()
                user_points = row[0] if row else 0
                
                # 2. Count users with more points
                cursor = conn.execute("SELECT COUNT(*) + 1 FROM user_activity WHERE guild_id = ? AND points_total > ?", (int(guild_id), user_points))
                return cursor.fetchone()[0]

    def log_role(self, user_id, guild_id, role_name, action='ADDED', timestamp=None):
        # Write down in the history that a role was added or removed
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        
        timestamp_str = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else timestamp
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO role_history (user_id, guild_id, role_name, action, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, guild_id, role_name, action, timestamp_str))
            conn.commit()

    def get_role_history(self, guild_id, limit=300):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, role_name, action, timestamp FROM role_history 
                WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (int(guild_id), limit))
            return cursor.fetchall()

    def update_game_activity(self, user_id, guild_id, game_name, bot_assigned=False):
        # Record which game someone is playing and if the bot gave them a role for it
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO game_activity (user_id, guild_id, role_name, last_played, bot_assigned)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id, role_name) DO UPDATE SET 
                    last_played = excluded.last_played,
                    bot_assigned = (CASE WHEN excluded.bot_assigned = 1 THEN 1 ELSE game_activity.bot_assigned END)
            """, (user_id, guild_id, game_name, now, 1 if bot_assigned else 0))
            conn.commit()

    def get_game_stats_report(self, guild_id, timeframe="alltime"):
        with self._get_connection() as conn:
            query = """
                SELECT 
                    CASE WHEN role_name LIKE 'Player: %' THEN SUBSTR(role_name, 9) ELSE role_name END as clean_name,
                    COUNT(DISTINCT user_id) as user_count,
                    SUM(total_minutes) as total_mins
                FROM game_activity 
                WHERE guild_id = ? {time_filter}
                GROUP BY clean_name 
                ORDER BY total_mins DESC
            """
            
            if timeframe == "monthly":
                cutoff = (datetime.datetime.now(datetime.timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)).isoformat()
                cursor = conn.execute(query.format(time_filter="AND last_played >= ?"), (int(guild_id), cutoff))
            else:
                cursor = conn.execute(query.format(time_filter=""), (int(guild_id),))
            
            return cursor.fetchall()

    def get_inactive_games(self, guild_id, days=30):
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, role_name FROM game_activity 
                WHERE guild_id = ? AND last_played < ? AND bot_assigned = 1
            """, (int(guild_id), cutoff))
            return cursor.fetchall()

    def remove_game_activity(self, user_id, guild_id, role_name):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM game_activity WHERE user_id = ? AND guild_id = ? AND role_name = ?", (int(user_id), int(guild_id), role_name))
            conn.commit()

    def get_user_recent_games(self, user_id, guild_id, limit=3):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT role_name FROM game_activity 
                WHERE user_id = ? AND guild_id = ? 
                ORDER BY last_played DESC LIMIT ?
            """, (int(user_id), int(guild_id), limit))
            return [row[0].replace("Player: ", "") for row in cursor.fetchall()]

    def get_user_top_games(self, user_id, guild_id, limit=3):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT role_name, total_minutes FROM game_activity 
                WHERE user_id = ? AND guild_id = ? 
                ORDER BY total_minutes DESC LIMIT ?
            """, (int(user_id), int(guild_id), limit))
            return cursor.fetchall()

    # --- ADVANCED TRACKING ---
    # These functions track extra things like who you talk to or who reacts to you

    def _record_overlaps(self, conn, user_id, guild_id, channel_id, start_time, end_time):
        # Find other sessions in the SAME channel that overlap with this one
        # Logic: overlap = session2.start < session1.end AND session2.end > session1.start
        cursor = conn.execute("""
            SELECT user_id, start_time, end_time 
            FROM voice_sessions 
            WHERE guild_id = ? AND channel_id = ? AND user_id != ?
              AND start_time < ? AND end_time > ?
        """, (guild_id, channel_id, user_id, end_time.isoformat(), start_time.isoformat()))
        
        rows = cursor.fetchall()
        today = start_time.date()
        
        for other_uid, o_start_str, o_end_str in rows:
            o_start = datetime.datetime.fromisoformat(o_start_str)
            o_end = datetime.datetime.fromisoformat(o_end_str)
            
            # Calculate overlap duration
            overlap_start = max(start_time, o_start)
            overlap_end = min(end_time, o_end)
            overlap_duration = (overlap_end - overlap_start).total_seconds() / 60.0
            
            if overlap_duration > 0:
                uid1, uid2 = min(user_id, other_uid), max(user_id, other_uid)
                conn.execute("""
                    INSERT INTO voice_overlaps (user_id1, user_id2, guild_id, date, overlap_minutes)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id1, user_id2, guild_id, date) DO UPDATE SET 
                        overlap_minutes = overlap_minutes + excluded.overlap_minutes
                """, (uid1, uid2, guild_id, today, overlap_duration))

    def log_voice_session(self, user_id, guild_id, channel_id, start_time, end_time, duration, stream_detail=None):
        # Save the details of a finished voice call (start time, end time, which room)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration_minutes, stream_detail)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, channel_id, start_time.isoformat(), end_time.isoformat(), duration, stream_detail))
            
            # Record overlaps for the cache table
            self._record_overlaps(conn, user_id, guild_id, channel_id, start_time, end_time)
            
            conn.commit()

    def log_reaction_interaction(self, user_id, target_user_id, guild_id, channel_id, message_id, emoji):
        # Save who reacted to whose message and with what emoji
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO reaction_history (user_id, target_user_id, guild_id, channel_id, message_id, emoji, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, target_user_id, guild_id, channel_id, message_id, emoji, now))
            conn.commit()

    def get_top_voice_partners(self, user_id, guild_id, days=30):
        # Much faster query using the pre-calculated overlaps table
        cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).date()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT partner_id, SUM(overlap_minutes) as total_overlap
                FROM (
                    SELECT user_id2 as partner_id, overlap_minutes FROM voice_overlaps
                    WHERE user_id1 = ? AND guild_id = ? AND date >= ?
                    UNION ALL
                    SELECT user_id1 as partner_id, overlap_minutes FROM voice_overlaps
                    WHERE user_id2 = ? AND guild_id = ? AND date >= ?
                )
                GROUP BY partner_id
                ORDER BY total_overlap DESC
                LIMIT 5
            """, (int(user_id), int(guild_id), cutoff_date, int(user_id), int(guild_id), cutoff_date))
            return cursor.fetchall()

    def get_user_social_stats(self, user_id, guild_id, days=30):
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        stats = {"top_channel": None, "top_emoji": None, "top_target": None}
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT channel_id, SUM(duration_minutes) as total FROM voice_sessions
                WHERE user_id = ? AND guild_id = ? AND start_time >= ?
                GROUP BY channel_id ORDER BY total DESC LIMIT 1
            """, (int(user_id), int(guild_id), cutoff))
            row = cursor.fetchone(); stats["top_channel"] = row[0] if row else None
            
            cursor = conn.execute("""
                SELECT emoji, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY emoji ORDER BY count DESC LIMIT 1
            """, (int(user_id), int(guild_id), cutoff))
            row = cursor.fetchone(); stats["top_emoji"] = row[0] if row else None
            
            cursor = conn.execute("""
                SELECT target_user_id, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY target_user_id ORDER BY count DESC LIMIT 1
            """, (int(user_id), int(guild_id), cutoff))
            row = cursor.fetchone(); stats["top_target"] = row[0] if row else None
        return stats

    # --- TRACKED GAMES MGMT ---

    def get_tracked_games(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT game_substring, role_suffix FROM tracked_games")
            return {row[0]: row[1] for row in cursor.fetchall()}

    def add_tracked_game(self, substring, suffix):
        with self._get_connection() as conn:
            conn.execute("INSERT OR REPLACE INTO tracked_games (game_substring, role_suffix) VALUES (?, ?)", (substring, suffix))
            conn.commit()

    # --- VOICE PERSISTENCE ---

    def start_voice_session(self, user_id, guild_id, channel_id, joined_at, multiplier=2.0, is_streaming=False, stream_name=None):
        joined_at_str = joined_at.isoformat() if isinstance(joined_at, datetime.datetime) else joined_at
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO active_voice_sessions (user_id, guild_id, channel_id, joined_at, multiplier, is_streaming, stream_name)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET 
                    joined_at = excluded.joined_at, 
                    channel_id = excluded.channel_id,
                    multiplier = excluded.multiplier,
                    is_streaming = excluded.is_streaming,
                    stream_name = excluded.stream_name
            """, (user_id, guild_id, channel_id, joined_at_str, multiplier, 1 if is_streaming else 0, stream_name))
            conn.commit()

    def end_voice_session(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT joined_at, multiplier, is_streaming, stream_name 
                FROM active_voice_sessions WHERE user_id = ? AND guild_id = ?
            """, (int(user_id), int(guild_id)))
            row = cursor.fetchone()
            if row:
                conn.execute("DELETE FROM active_voice_sessions WHERE user_id = ? AND guild_id = ?", (int(user_id), int(guild_id)))
                conn.commit()
                joined_at = datetime.datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
                return {
                    "joined_at": joined_at,
                    "multiplier": row[1],
                    "is_streaming": bool(row[2]),
                    "stream_name": row[3]
                }
            return None

    def get_active_voice_sessions(self, guild_id=None):
        with self._get_connection() as conn:
            if guild_id:
                cursor = conn.execute("SELECT user_id, joined_at, multiplier, is_streaming, stream_name FROM active_voice_sessions WHERE guild_id = ?", (int(guild_id),))
            else:
                cursor = conn.execute("SELECT user_id, joined_at, multiplier, is_streaming, stream_name FROM active_voice_sessions")
            
            rows = cursor.fetchall()
            return {row[0]: {
                "joined_at": (datetime.datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]),
                "multiplier": row[2],
                "is_streaming": bool(row[3]),
                "stream_name": row[4]
            } for row in rows}

    # --- GAME PERSISTENCE ---

    def start_game_session(self, user_id, guild_id, game_name, started_at):
        ts = started_at.isoformat() if isinstance(started_at, datetime.datetime) else started_at
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO active_game_sessions (user_id, guild_id, game_name, started_at)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, game_name, ts))
            conn.commit()

    def end_game_session(self, user_id, guild_id, game_name):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT started_at FROM active_game_sessions WHERE user_id = ? AND guild_id = ? AND game_name = ?", (int(user_id), int(guild_id), game_name))
            row = cursor.fetchone()
            if row:
                conn.execute("DELETE FROM active_game_sessions WHERE user_id = ? AND guild_id = ? AND game_name = ?", (int(user_id), int(guild_id), game_name))
                conn.commit()
                return datetime.datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            return None

    def get_active_game_sessions(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT user_id, guild_id, game_name, started_at FROM active_game_sessions")
            return {(row[0], row[1], row[2]): (datetime.datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3]) for row in cursor.fetchall()}

    def add_game_minutes(self, user_id, guild_id, game_name, minutes):
        today = datetime.date.today()
        with self._get_connection() as conn:
            # 1. Total (per game)
            conn.execute("""
                UPDATE game_activity SET total_minutes = total_minutes + ? 
                WHERE user_id = ? AND guild_id = ? AND role_name = ?
            """, (minutes, int(user_id), int(guild_id), game_name))
            
            # 2. Daily Summary
            conn.execute("""
                    game_minutes = game_minutes + ?
            """, (int(user_id), int(guild_id), today, minutes, minutes))
            
            # 3. Daily Per-Game (for Variety)
            conn.execute("""
                ON CONFLICT(user_id, guild_id, game_name, date) DO UPDATE SET 
                    minutes = minutes + ?
            """, (int(user_id), int(guild_id), game_name, today, minutes, minutes))
            
            conn.commit()

    def get_weekly_champion_stats(self, guild_id, start_date, end_date):
        # Fetches top performers for each category in the given timeframe
        with self._get_connection() as conn:
            # 1. Spotify
            spotify_top = conn.execute("""
                SELECT user_id, SUM(spotify_minutes) as total FROM daily_stats 
                WHERE guild_id = ? AND date >= ? AND date <= ?
                GROUP BY user_id ORDER BY total DESC LIMIT 1
            """, (guild_id, start_date, end_date)).fetchone()
            
            # 2. Hardcore Gamer (Total Minutes)
            # We need to query daily_stats for overall gaming minutes if we track them per-day...
            # Wait, game_activity doesn't have a date per-session in a way that's easy to query for 'past week'
            # without join. Let's look at how we track game minutes.
            # actually we don't have per-day game minutes in daily_stats currently!
            # I should have added that. Let's add 'game_minutes' to daily_stats migration too.
            game_top = conn.execute("""
                SELECT user_id, SUM(game_minutes) as total FROM daily_stats 
                WHERE guild_id = ? AND date >= ? AND date <= ?
                GROUP BY user_id ORDER BY total DESC LIMIT 1
            """, (guild_id, start_date, end_date)).fetchone()

            # 3. Variety Gamer (Most unique games played for >= X mins)
            variety_top = conn.execute(f"""
                SELECT user_id, COUNT(DISTINCT game_name) as variety FROM daily_game_stats
                WHERE guild_id = ? AND date >= ? AND date <= ? AND minutes >= {Config.VARIETY_MIN_MINUTES}
                GROUP BY user_id ORDER BY variety DESC LIMIT 1
            """, (guild_id, start_date, end_date)).fetchone()
            
            # 4. Streamer
            stream_top = conn.execute("""
                SELECT user_id, SUM(stream_minutes) as total FROM daily_stats 
                WHERE guild_id = ? AND date >= ? AND date <= ?
                GROUP BY user_id ORDER BY total DESC LIMIT 1
            """, (guild_id, start_date, end_date)).fetchone()
            
            # 5. Media (MemeLord)
            media_top = conn.execute("""
                SELECT user_id, SUM(media_count) as total FROM daily_stats 
                WHERE guild_id = ? AND date >= ? AND date <= ?
                GROUP BY user_id ORDER BY total DESC LIMIT 1
            """, (guild_id, start_date, end_date)).fetchone()
            
            return {
                "spotify": spotify_top,
                "gamer_total": game_top,
                "gamer_variety": variety_top,
                "streamer": stream_top,
                "media": media_top
            }

    def get_user_weekly_champion_stats(self, user_id, guild_id, start_date, end_date):
        # Fetches performance for a specific user in each category
        with self._get_connection() as conn:
            # 1. Spotify
            spotify = conn.execute("""
                SELECT SUM(spotify_minutes) FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ? AND date <= ?
            """, (user_id, guild_id, start_date, end_date)).fetchone()
            
            # 2. Hardcore Gamer
            game = conn.execute("""
                SELECT SUM(game_minutes) FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ? AND date <= ?
            """, (user_id, guild_id, start_date, end_date)).fetchone()

            # 3. Variety Gamer
            variety = conn.execute(f"""
                SELECT COUNT(DISTINCT game_name) FROM daily_game_stats
                WHERE user_id = ? AND guild_id = ? AND date >= ? AND date <= ? AND minutes >= {Config.VARIETY_MIN_MINUTES}
            """, (user_id, guild_id, start_date, end_date)).fetchone()
            
            # 4. Streamer
            stream = conn.execute("""
                SELECT SUM(stream_minutes) FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ? AND date <= ?
            """, (user_id, guild_id, start_date, end_date)).fetchone()
            
            # 5. Media
            media = conn.execute("""
                SELECT SUM(media_count) FROM daily_stats 
                WHERE user_id = ? AND guild_id = ? AND date >= ? AND date <= ?
            """, (user_id, guild_id, start_date, end_date)).fetchone()
            
            return {
                "spotify": spotify[0] if spotify and spotify[0] is not None else 0,
                "gamer_total": game[0] if game and game[0] is not None else 0,
                "gamer_variety": variety[0] if variety and variety[0] is not None else 0,
                "streamer": stream[0] if stream and stream[0] is not None else 0,
                "media": media[0] if media and media[0] is not None else 0
            }

    def log_champion_win(self, user_id, guild_id, category, win_date):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO champion_history (user_id, guild_id, category, win_date)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, category, win_date))
            conn.commit()

    def get_champion_wins(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT category, COUNT(*) FROM champion_history 
                WHERE user_id = ? AND guild_id = ?
                GROUP BY category
            """, (int(user_id), int(guild_id)))
            return dict(cursor.fetchall())

    def get_last_champions(self, guild_id):
        # Finds the winners from the most recent win_date in the history
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT category, user_id FROM champion_history 
                WHERE guild_id = ? AND win_date = (SELECT MAX(win_date) FROM champion_history WHERE guild_id = ?)
            """, (int(guild_id), int(guild_id)))
            return dict(cursor.fetchall())

    def reset_database(self):
        # DANGER: This wipes everything clean! All stats will be gone.
        tables = ["user_activity", "daily_stats", "role_history", "game_activity", "voice_sessions", "reaction_history", "active_voice_sessions", "active_game_sessions", "membership_history"]
        with self._get_connection() as conn:
            for table in tables: conn.execute(f"DELETE FROM {table}")
            conn.commit()

    def log_membership_event(self, user_id, guild_id, action, timestamp=None):
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc)
        ts_str = timestamp.isoformat() if isinstance(timestamp, datetime.datetime) else timestamp
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO membership_history (user_id, guild_id, action, timestamp)
                VALUES (?, ?, ?, ?)
            """, (user_id, guild_id, action, ts_str))
            conn.commit()

    def update_join_date(self, user_id, guild_id, joined_at):
        ts_str = joined_at.isoformat() if isinstance(joined_at, datetime.datetime) else joined_at
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE user_activity SET joined_at = ? WHERE user_id = ? AND guild_id = ?
            """, (ts_str, int(user_id), int(guild_id)))
            conn.commit()

    def get_user_join_date(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT joined_at FROM user_activity WHERE user_id = ? AND guild_id = ?", (int(user_id), int(guild_id)))
            row = cursor.fetchone()
            return datetime.datetime.fromisoformat(row[0]) if row and row[0] else None

    def get_membership_logs(self, guild_id, limit=300):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, action, timestamp FROM membership_history 
                WHERE guild_id = ? ORDER BY timestamp DESC LIMIT ?
            """, (int(guild_id), limit))
            return cursor.fetchall()

    # --- VISUAL ANALYSIS QUERIES ---
    
    def get_peak_activity_raw(self, guild_id, days=None):
        cutoff = None
        if days:
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        
        with self._get_connection() as conn:
            # Reactions count by day and hour
            react_query = "SELECT strftime('%w', timestamp) as d, strftime('%H', timestamp) as h, COUNT(*) FROM reaction_history WHERE guild_id = ?"
            react_params = [guild_id]
            if cutoff:
                react_query += " AND timestamp >= ?"
                react_params.append(cutoff)
            react_query += " GROUP BY d, h"
            
            # Voice start counts by day and hour
            voice_query = "SELECT strftime('%w', start_time) as d, strftime('%H', start_time) as h, COUNT(*) FROM voice_sessions WHERE guild_id = ?"
            voice_params = [guild_id]
            if cutoff:
                voice_query += " AND start_time >= ?"
                voice_params.append(cutoff)
            voice_query += " GROUP BY d, h"
            
            r_data = conn.execute(react_query, react_params).fetchall()
            v_data = conn.execute(voice_query, voice_params).fetchall()
            
            # Combine them: List of (day, hour, count)
            return r_data + v_data

    def get_voice_usage_raw(self, guild_id, days=None):
        query = "SELECT channel_id, SUM(duration_minutes) as total FROM voice_sessions WHERE guild_id = ?"
        params = [guild_id]
        if days:
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
            query += " AND start_time >= ?"
            params.append(cutoff)
        query += " GROUP BY channel_id ORDER BY total DESC LIMIT 10"
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def get_user_average_voice_duration(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT AVG(duration_minutes) FROM voice_sessions 
                WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            row = cursor.fetchone()
            return row[0] if row and row[0] else 0

    def get_top_average_voice_duration(self, guild_id, days=None):
        query = """
            SELECT user_id, AVG(duration_minutes) as avg_dur 
            FROM voice_sessions 
            WHERE guild_id = ? {time_filter}
            GROUP BY user_id 
            HAVING COUNT(*) >= 3
            ORDER BY avg_dur DESC 
            LIMIT 10
        """
        params = [guild_id]
        if days:
            cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
            query = query.replace("{time_filter}", "AND start_time >= ?")
            params.append(cutoff)
        else:
            query = query.replace("{time_filter}", "")
            
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def get_game_top_players(self, guild_id, game_name):
        with self._get_connection() as conn:
            # Matches both direct name and 'Player: Name' format
            query = """
                SELECT user_id, total_minutes, last_played 
                FROM game_activity 
                WHERE guild_id = ? AND (role_name = ? OR role_name = ?)
                ORDER BY total_minutes DESC
            """
            alt_name = f"Player: {game_name}" if not game_name.startswith("Player: ") else game_name
            raw_name = game_name.replace("Player: ", "")
            
            return conn.execute(query, (int(guild_id), raw_name, alt_name)).fetchall()

    def get_all_unique_games(self, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT 
                CASE WHEN role_name LIKE 'Player: %' THEN SUBSTR(role_name, 9) ELSE role_name END as clean_name
                FROM game_activity 
                WHERE guild_id = ?
            """, (guild_id,))
            return [row[0] for row in cursor.fetchall() if row[0]]

    def get_channel_activity_raw(self, guild_id, days=None):
        query = "SELECT channel_id, SUM(messages) as total FROM daily_stats WHERE guild_id = ? AND channel_id != 0"
        params = [int(guild_id)]
        if days:
            cutoff = (datetime.date.today() - datetime.timedelta(days=days)).isoformat()
            query += " AND date >= ?"
            params.append(cutoff)
        query += " GROUP BY channel_id ORDER BY total DESC LIMIT 10"
        with self._get_connection() as conn:
            return conn.execute(query, params).fetchall()

    def get_stream_history(self, guild_id, days=7):
        # Get a list of recent voice sessions that included streaming
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, start_time, duration_minutes, stream_detail, channel_id
                FROM voice_sessions 
                WHERE guild_id = ? AND stream_detail IS NOT NULL AND start_time >= ?
                ORDER BY start_time DESC
            """, (int(guild_id), cutoff))
            return cursor.fetchall()

    def get_user_average_voice_duration(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT AVG(duration_minutes) FROM voice_sessions 
                WHERE user_id = ? AND guild_id = ?
            """, (int(user_id), int(guild_id)))
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0

    def migrate_voice_overlaps(self):
        # One-time migration to populate voice_overlaps from voice_sessions
        with self._get_connection() as conn:
            # Check if already migrated (simple check: is the table empty?)
            count = conn.execute("SELECT COUNT(*) FROM voice_overlaps").fetchone()[0]
            if count > 0:
                return # Already has data
                
            print("Migrating voice overlaps... this may take a moment.")
            # This query is basically the old get_top_voice_partners logic but for EVERYONE
            cursor = conn.execute("""
                SELECT s1.user_id, s2.user_id, s1.guild_id, date(s1.start_time),
                       SUM((MIN(julianday(s1.end_time), julianday(s2.end_time)) - 
                            MAX(julianday(s1.start_time), julianday(s2.start_time))) * 1440.0) as duration
                FROM voice_sessions s1
                JOIN voice_sessions s2 ON s1.guild_id = s2.guild_id 
                     AND s1.channel_id = s2.channel_id
                     AND s1.user_id < s2.user_id
                WHERE s2.start_time < s1.end_time 
                  AND s2.end_time > s1.start_time
                GROUP BY s1.user_id, s2.user_id, s1.guild_id, date(s1.start_time)
            """)
            
            rows = cursor.fetchall()
            if rows:
                conn.executemany("""
                    INSERT INTO voice_overlaps (user_id1, user_id2, guild_id, date, overlap_minutes)
                    VALUES (?, ?, ?, ?, ?)
                """, rows)
                conn.commit()
            print(f"Migration complete. {len(rows)} overlap records created.")
