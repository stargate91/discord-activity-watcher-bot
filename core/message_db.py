import sqlite3
import datetime
import os

class MessageArchiveDB:
    def __init__(self, db_path="message_archive.db"):
        self.db_path = db_path
        self._create_table()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _create_table(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    message_id INTEGER PRIMARY KEY,
                    guild_id INTEGER,
                    channel_id INTEGER,
                    user_id INTEGER,
                    username TEXT,
                    content TEXT,
                    attachments TEXT,
                    timestamp TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp)")
            conn.commit()

    def insert_message(self, message_id, guild_id, channel_id, user_id, username, content, attachments, timestamp):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO messages (message_id, guild_id, channel_id, user_id, username, content, attachments, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (message_id, guild_id, channel_id, user_id, username, content, attachments, timestamp.isoformat()))
            conn.commit()

    def update_message_content(self, message_id, new_content):
        with self._get_connection() as conn:
            conn.execute("UPDATE messages SET content = ? WHERE message_id = ?", (new_content, message_id))
            conn.commit()

    def get_message(self, message_id):
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT user_id, username, content, attachments, timestamp FROM messages WHERE message_id = ?", (message_id,))
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row[0],
                    "username": row[1],
                    "content": row[2],
                    "attachments": row[3],
                    "timestamp": datetime.datetime.fromisoformat(row[4])
                }
            return None

    def get_db_size_mb(self):
        if not os.path.exists(self.db_path):
            return 0
        return os.path.getsize(self.db_path) / (1024 * 1024)

    def prune_database(self, retention_days=None, max_size_mb=None):
        deleted_count = 0
        
        # 1. Prune by age
        if retention_days and retention_days > 0:
            with self._get_connection() as conn:
                cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=retention_days)
                cursor = conn.execute("DELETE FROM messages WHERE timestamp < ?", (cutoff_date.isoformat(),))
                deleted_count += cursor.rowcount
                conn.commit()

        # 2. Prune by size
        if max_size_mb and max_size_mb > 0:
            if self.get_db_size_mb() > max_size_mb:
                with self._get_connection() as conn:
                    cursor = conn.execute("SELECT COUNT(*) FROM messages")
                    count = cursor.fetchone()[0]
                    if count > 0:
                        # Drop the oldest 20% to gain breathing room
                        limit = max(1, int(count * 0.2))
                        cursor = conn.execute(f"""
                            DELETE FROM messages WHERE message_id IN (
                                SELECT message_id FROM messages ORDER BY timestamp ASC LIMIT {limit}
                            )
                        """)
                        deleted_count += cursor.rowcount
                        conn.commit()
                        
                # VACUUM reclaims physically freed space
                with self._get_connection() as conn:
                    conn.execute("VACUUM")
        
        return deleted_count
