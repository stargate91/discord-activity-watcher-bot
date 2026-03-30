import sqlite3
import datetime

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
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
            # daily_stats: Remembers what happened each day so we can make weekly/monthly charts
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
                    duration_minutes REAL
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
                    PRIMARY KEY (user_id, guild_id)
                )
            """)
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
            
            # Migrations for user_activity
            for col, ctype in [("returned_at", "TIMESTAMP DEFAULT NULL"), ("message_count", "INTEGER DEFAULT 0"), 
                               ("reaction_count", "INTEGER DEFAULT 0"), ("voice_minutes", "REAL DEFAULT 0")]:
                try: conn.execute(f"ALTER TABLE user_activity ADD COLUMN {col} {ctype}")
                except sqlite3.OperationalError: pass
            
            # Migrations for role_history
            try: conn.execute("ALTER TABLE role_history ADD COLUMN action TEXT DEFAULT 'ADDED'")
            except sqlite3.OperationalError: pass

            # Migrations for game_activity
            try: conn.execute("ALTER TABLE game_activity ADD COLUMN total_minutes REAL DEFAULT 0")
            except sqlite3.OperationalError: pass
            
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

    def increment_messages(self, user_id, guild_id):
        # Add 1 to the message count for a user (both total and for today)
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
        # Add 1 to the reaction count for a user (both total and for today)
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
        # Add the minutes someone spent in voice to their stats
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
        # Get the top players for the leaderboard (last X days or all-time)
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
            """, (guild_id, limit))
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

    def get_user_recent_games(self, user_id, guild_id, limit=3):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT role_name FROM game_activity 
                WHERE user_id = ? AND guild_id = ? 
                ORDER BY last_played DESC LIMIT ?
            """, (user_id, guild_id, limit))
            return [row[0].replace("Player: ", "") for row in cursor.fetchall()]

    def get_user_top_games(self, user_id, guild_id, limit=3):
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT role_name, total_minutes FROM game_activity 
                WHERE user_id = ? AND guild_id = ? 
                ORDER BY total_minutes DESC LIMIT ?
            """, (user_id, guild_id, limit))
            return cursor.fetchall()

    # --- ADVANCED TRACKING ---
    # These functions track extra things like who you talk to or who reacts to you

    def log_voice_session(self, user_id, guild_id, channel_id, start_time, end_time, duration):
        # Save the details of a finished voice call (start time, end time, which room)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO voice_sessions (user_id, guild_id, channel_id, start_time, end_time, duration_minutes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, guild_id, channel_id, start_time.isoformat(), end_time.isoformat(), duration))
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
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT s2.user_id, SUM(
                    (MIN(julianday(s1.end_time), julianday(s2.end_time)) - 
                     MAX(julianday(s1.start_time), julianday(s2.start_time))) * 1440.0
                ) as overlap_mins
                FROM voice_sessions s1
                JOIN voice_sessions s2 ON s1.guild_id = s2.guild_id 
                    AND s1.channel_id = s2.channel_id
                    AND s1.user_id != s2.user_id
                WHERE s1.user_id = ? 
                    AND s1.start_time >= ?
                    AND s2.start_time < s1.end_time 
                    AND s2.end_time > s1.start_time
                GROUP BY s2.user_id
                ORDER BY overlap_mins DESC
                LIMIT 5
            """, (user_id, cutoff))
            return cursor.fetchall()

    def get_user_social_stats(self, user_id, guild_id, days=30):
        cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat()
        stats = {"top_channel": None, "top_emoji": None, "top_target": None}
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT channel_id, SUM(duration_minutes) as total FROM voice_sessions
                WHERE user_id = ? AND guild_id = ? AND start_time >= ?
                GROUP BY channel_id ORDER BY total DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
            row = cursor.fetchone(); stats["top_channel"] = row[0] if row else None
            
            cursor = conn.execute("""
                SELECT emoji, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY emoji ORDER BY count DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
            row = cursor.fetchone(); stats["top_emoji"] = row[0] if row else None
            
            cursor = conn.execute("""
                SELECT target_user_id, COUNT(*) as count FROM reaction_history
                WHERE user_id = ? AND guild_id = ? AND timestamp >= ?
                GROUP BY target_user_id ORDER BY count DESC LIMIT 1
            """, (user_id, guild_id, cutoff))
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

    def start_voice_session(self, user_id, guild_id, channel_id, joined_at):
        joined_at_str = joined_at.isoformat() if isinstance(joined_at, datetime.datetime) else joined_at
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO active_voice_sessions (user_id, guild_id, channel_id, joined_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, guild_id) DO UPDATE SET joined_at = excluded.joined_at, channel_id = excluded.channel_id
            """, (user_id, guild_id, channel_id, joined_at_str))
            conn.commit()

    def end_voice_session(self, user_id, guild_id):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT joined_at FROM active_voice_sessions WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
            row = cursor.fetchone()
            if row:
                conn.execute("DELETE FROM active_voice_sessions WHERE user_id = ? AND guild_id = ?", (user_id, guild_id))
                conn.commit()
                return datetime.datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            return None

    def get_active_voice_sessions(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT user_id, joined_at FROM active_voice_sessions")
            return {row[0]: (datetime.datetime.fromisoformat(row[1]) if isinstance(row[1], str) else row[1]) for row in cursor.fetchall()}

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
            cursor = conn.execute("SELECT started_at FROM active_game_sessions WHERE user_id = ? AND guild_id = ? AND game_name = ?", (user_id, guild_id, game_name))
            row = cursor.fetchone()
            if row:
                conn.execute("DELETE FROM active_game_sessions WHERE user_id = ? AND guild_id = ? AND game_name = ?", (user_id, guild_id, game_name))
                conn.commit()
                return datetime.datetime.fromisoformat(row[0]) if isinstance(row[0], str) else row[0]
            return None

    def get_active_game_sessions(self):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT user_id, guild_id, game_name, started_at FROM active_game_sessions")
            return {(row[0], row[1], row[2]): (datetime.datetime.fromisoformat(row[3]) if isinstance(row[3], str) else row[3]) for row in cursor.fetchall()}

    def add_game_minutes(self, user_id, guild_id, game_name, minutes):
        with self._get_connection() as conn:
            conn.execute("""
                UPDATE game_activity SET total_minutes = total_minutes + ? 
                WHERE user_id = ? AND guild_id = ? AND role_name = ?
            """, (minutes, user_id, guild_id, game_name))
            conn.commit()

    def reset_database(self):
        # DANGER: This wipes everything clean! All stats will be gone.
        tables = ["user_activity", "daily_stats", "role_history", "game_activity", "voice_sessions", "reaction_history", "active_voice_sessions", "active_game_sessions"]
        with self._get_connection() as conn:
            for table in tables: conn.execute(f"DELETE FROM {table}")
            conn.commit()

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
