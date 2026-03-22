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
            # Migrations
            columns = [
                ("returned_at", "TIMESTAMP DEFAULT NULL"),
                ("message_count", "INTEGER DEFAULT 0"),
                ("reaction_count", "INTEGER DEFAULT 0"),
                ("voice_minutes", "REAL DEFAULT 0")
            ]
            for col_name, col_type in columns:
                try:
                    conn.execute(f"ALTER TABLE user_activity ADD COLUMN {col_name} {col_type}")
                except sqlite3.OperationalError: pass
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


