import sqlite3
import datetime

class DBManager:
    def __init__(self, db_path="activity.db"):
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._get_connection() as conn:
            # Total stats (for inactivity and all-time)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
                    last_active TIMESTAMP,
                    returned_at TIMESTAMP DEFAULT NULL,
                    message_count INTEGER DEFAULT 0,
                    reaction_count INTEGER DEFAULT 0,
                    voice_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            # Historical stats (for leaderboards)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    user_id INTEGER,
                    guild_id INTEGER,
                    date DATE,
                    messages INTEGER DEFAULT 0,
                    reactions INTEGER DEFAULT 0,
                    voice_minutes REAL DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, date)
                )
            """)
            # Role history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS role_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    role_name TEXT,
                    timestamp TIMESTAMP
                )
            """)
            # Game activity (for auto role removal)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_activity (
                    user_id INTEGER,
                    guild_id INTEGER,
                    role_name TEXT,
                    last_played TIMESTAMP,
                    bot_assigned INTEGER DEFAULT 0,
                    PRIMARY KEY (user_id, guild_id, role_name)
                )
            """)
            # Detailed Voice Sessions (Which channel, how long)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_minutes REAL
                )
            """)
            # Reaction Interactions (Who to Whom)
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
            # Tracked Game Franchises (substring -> role_suffix)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tracked_games (
                    game_substring TEXT PRIMARY KEY,
                    role_suffix TEXT
                )
            """)
            
            # Migrations for user_activity
            for col, ctype in [("returned_at", "TIMESTAMP DEFAULT NULL"), ("message_count", "INTEGER DEFAULT 0"), 
                               ("reaction_count", "INTEGER DEFAULT 0"), ("voice_minutes", "REAL DEFAULT 0")]:
                try: conn.execute(f"ALTER TABLE user_activity ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError: pass
            
            # Migrations for role_history
            try: conn.execute("ALTER TABLE role_history ADD COLUMN action TEXT DEFAULT 'ADDED'")
            except sqlite3.OperationalError: pass
            
            conn.commit()
            conn.commit()




    def update_activity(self, user_id, guild_id, last_active=None):
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
        """Sets when the user returned from inactivity."""
        timestamp_str = timestamp.isoformat() if timestamp else None
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE user_activity SET returned_at = ? WHERE user_id = ? AND guild_id = ?
            """, (timestamp_str, user_id, guild_id))
            conn.commit()

    def increment_messages(self, user_id, guild_id):
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("UPDATE user_activity SET message_count = message_count + 1 WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, date, messages) VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, guild_id, date) DO UPDATE SET messages = messages + 1
            """, (user_id, guild_id, today))
            conn.commit()

    def increment_reactions(self, user_id, guild_id):
        today = datetime.date.today()
        with self._get_connection() as conn:
            # Total
            conn.execute("UPDATE user_activity SET reaction_count = reaction_count + 1 WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, date, reactions) VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, guild_id, date) DO UPDATE SET reactions = reactions + 1
            """, (user_id, guild_id, today))
            conn.commit()

    def add_voice_minutes(self, user_id, guild_id, minutes):
        today = datetime.date.today()
        # Use float (REAL in SQLite) for better precision across moves
        with self._get_connection() as conn:
            # Total
            conn.execute("UPDATE user_activity SET voice_minutes = voice_minutes + ? WHERE user_id = ? AND guild_id = ?", (minutes, user_id, guild_id))
            # Daily
            conn.execute("""
                INSERT INTO daily_stats (user_id, guild_id, date, voice_minutes) VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id, date) DO UPDATE SET voice_minutes = voice_minutes + ?
            """, (user_id, guild_id, today, minutes, minutes))
            conn.commit()

    def get_leaderboard_data(self, guild_id, days=None):
        """Returns summed stats for the last X days, or all time if days is None."""
        with self._get_connection() as conn:
            if days:
                cutoff_date = datetime.date.today() - datetime.timedelta(days=days)
                cursor = conn.execute("""
                    SELECT user_id, SUM(messages), SUM(reactions), SUM(voice_minutes) 
                    FROM daily_stats WHERE guild_id = ? AND date >= ? 
                    GROUP BY user_id
                """, (guild_id, cutoff_date))
            else:
                cursor = conn.execute("""
                    SELECT user_id, message_count, reaction_count, voice_minutes 
                    FROM user_activity WHERE guild_id = ?
                """, (guild_id,))
            
            rows = cursor.fetchall()
            return {row[0]: {"messages": row[1] or 0, "reactions": row[2] or 0, "voice": row[3] or 0} for row in rows}


    def get_user_data(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT last_active, returned_at, message_count, reaction_count, voice_minutes 
                FROM user_activity WHERE user_id = ? AND guild_id = ?
            """, (user_id, guild_id))
            row = cursor.fetchone()
            if row:
                last_active = datetime.datetime.fromisoformat(row[0])
                returned_at = datetime.datetime.fromisoformat(row[1]) if row[1] else None
                return {
                    "last_active": last_active, 
                    "returned_at": returned_at,
                    "message_count": row[2],
                    "reaction_count": row[3],
                    "voice_minutes": row[4]
                }
            return None

    def get_all_guild_data(self, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, last_active, returned_at, message_count, reaction_count, voice_minutes 
                FROM user_activity WHERE guild_id = ?
            """, (guild_id,))
            rows = cursor.fetchall()
            data = {}
            for row in rows:
                data[row[0]] = {
                    "last_active": datetime.datetime.fromisoformat(row[1]),
                    "returned_at": datetime.datetime.fromisoformat(row[2]) if row[2] else None,
                    "message_count": row[3],
                    "reaction_count": row[4],
                    "voice_minutes": row[5]
                }
            return data

    def log_role(self, user_id, guild_id, role_name, action='ADDED', timestamp=None):
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
            """, (guild_id, limit))
            return cursor.fetchall()

    def update_game_activity(self, user_id, guild_id, game_name, bot_assigned=False):
        """Updates or inserts a game activity record. bot_assigned is True if the bot gave a role for it."""
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
        """Returns the number of unique players per game, merging role-based and raw activity."""
        with self._get_connection() as conn:
            # We use a CASE to strip 'Player: ' in the grouping, so 'Dota 2' and 'Player: Dota 2' merge.
            # We count DISTINCT user_id across the merged groups.
            query = """
                SELECT 
                    CASE WHEN role_name LIKE 'Player: %' THEN SUBSTR(role_name, 9) ELSE role_name END as clean_name,
                    COUNT(DISTINCT user_id) as user_count 
                FROM game_activity 
                WHERE guild_id = ? {time_filter}
                GROUP BY clean_name 
                ORDER BY user_count DESC
            """
            
            if timeframe == "monthly":
                # Start of current month
                cutoff = datetime.datetime.now(datetime.timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
                cursor = conn.execute(query.format(time_filter="AND last_played >= ?"), (guild_id, cutoff))
            else:
                cursor = conn.execute(query.format(time_filter=""), (guild_id,))
            
            return cursor.fetchall()

    def get_inactive_games(self, guild_id, days=30):
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, role_name FROM game_activity 
                WHERE guild_id = ? AND last_played < ? AND bot_assigned = 1
            """, (guild_id, cutoff))
            return cursor.fetchall()

    def remove_game_activity(self, user_id, guild_id, role_name):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM game_activity WHERE user_id = ? AND guild_id = ? AND role_name = ?", (user_id, guild_id, role_name))
            conn.commit()

    # --- ADVANCED TRACKING ---

    def log_voice_session(self, user_id, guild_id, channel_id, start_time, end_time, duration):
        """Logs a specific voice session for detailed analytics."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, channel_id, start_time.isoformat(), end_time.isoformat(), duration))
            conn.commit()

    def log_reaction_interaction(self, user_id, target_user_id, guild_id, channel_id, message_id, emoji):
        """Logs who reacted to whose post for 'social connection' stats."""
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO reaction_history (user_id, target_user_id, guild_id, channel_id, message_id, emoji, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, target_user_id, guild_id, channel_id, message_id, emoji, now))
            conn.commit()

    def get_top_voice_partners(self, user_id, guild_id, days=7):
        """Finds who the user spent the most time with in voice (Experimental)."""
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            # This is a complex query: find other sessions that overlap in the same channel
            cursor = conn.execute("""
                SELECT v2.user_id, SUM(
                    (MIN(julianday(v1.end_time), julianday(v2.end_time)) - 
                     MAX(julianday(v1.start_time), julianday(v2.start_time))) * 1440
                ) as overlap_mins
                FROM voice_sessions v1
                JOIN voice_sessions v2 ON v1.channel_id = v2.channel_id 
                    AND v1.user_id != v2.user_id
                    AND v1.guild_id = v2.guild_id
                WHERE v1.user_id = ? AND v1.guild_id = ? AND v1.start_time >= ?
                    AND v2.start_time < v1.end_time AND v2.end_time > v1.start_time
                GROUP BY v2.user_id
                ORDER BY overlap_mins DESC
                LIMIT 5
            """, (user_id, guild_id, cutoff))
            return cursor.fetchall()

    def get_user_social_stats(self, user_id, guild_id, days=30):
        """Fetches advanced social stats for a user (Top Channel, Top Emoji, Top Target)."""
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        stats = {"top_channel": None, "top_emoji": None, "top_target": None}
        
        with self._get_connection() as conn:
            # Top Channel
            cursor = conn.execute("""
                SELECT channel_id, SUM(duration_minutes) as total FROM voice_sessions
                WHERE user_id = ? AND guild_id = ? AND start_time >= ?
                GROUP BY channel_id ORDER BY total DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
            row = cursor.fetchone()
            if row: stats["top_channel"] = row[0]
            
            # Top Emoji used by user
            cursor = conn.execute("""
                SELECT emoji, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY emoji ORDER BY count DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
            row = cursor.fetchone()
            if row: stats["top_emoji"] = row[0]
            
            # Top person the user reacts to
            cursor = conn.execute("""
                SELECT target_user_id, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY target_user_id ORDER BY count DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
            row = cursor.fetchone()
            if row: stats["top_target"] = row[0]
            
        return stats

    # --- DYNAMIC GAME TRACKING ---

    def add_tracked_game(self, substring, role_suffix):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO tracked_games (game_substring, role_suffix)
                VALUES (?, ?)
                ON CONFLICT(game_substring) DO UPDATE SET role_suffix = excluded.role_suffix
            """, (substring, role_suffix))
            conn.commit()

    def get_tracked_games(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT game_substring, role_suffix FROM tracked_games")
            return dict(cursor.fetchall())
    
    def remove_tracked_game(self, substring):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM tracked_games WHERE game_substring = ?", (substring,))
            conn.commit()
    def get_user_recent_games(self, user_id, guild_id, limit=3):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT role_name FROM game_activity 
                WHERE user_id = ? AND guild_id = ? 
                ORDER BY last_played DESC LIMIT ?
            """, (user_id, guild_id, limit))
            return [row[0].replace("Player: ", "") for row in cursor.fetchall()]


