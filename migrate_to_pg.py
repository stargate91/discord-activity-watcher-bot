import sqlite3
import psycopg2
from psycopg2 import extras
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

SQLITE_ACTIVITY_DB = "activity.db"
SQLITE_MESSAGE_DB = "message_archive.db"
POSTGRES_URL = os.getenv("DATABASE_URL")
DEFAULT_GUILD_ID = 1083433370815582240 # Change this to your main guild ID if needed

def migrate_activity_db():
    print("Migrating activity database...")
    if not os.path.exists(SQLITE_ACTIVITY_DB):
        print(f"File {SQLITE_ACTIVITY_DB} not found, skipping.")
        return

    lite_conn = sqlite3.connect(SQLITE_ACTIVITY_DB)
    pg_conn = psycopg2.connect(POSTGRES_URL)
    
    tables = [
        "user_activity", "daily_stats", "daily_game_stats", "role_history", 
        "game_activity", "voice_sessions", "reaction_history", "membership_history",
        "active_voice_sessions", "active_game_sessions", "elite_history", 
        "voice_overlaps"
    ]

    for table in tables:
        print(f"  Processing {table}...")
        lite_cur = lite_conn.cursor()
        lite_cur.execute(f"SELECT * FROM {table}")
        rows = lite_cur.fetchall()
        
        if not rows:
            continue
            
        columns = [description[0] for description in lite_cur.description]
        placeholders = ",".join(["%s"] * len(columns))
        
        with pg_conn.cursor() as pg_cur:
            # Handle sequence reset for SERIAL columns if needed
            if table in ["role_history", "voice_sessions", "reaction_history", "membership_history", "elite_history"]:
                pg_cur.execute(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE")
            else:
                pg_cur.execute(f"DELETE FROM {table}")
                
            query = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"
            pg_cur.executemany(query, rows)
        pg_conn.commit()

    # Special handling for tracked_games and reaction_role_messages (new guild_id PK)
    print("  Processing tracked_games (with default guild_id)...")
    lite_cur.execute("SELECT * FROM tracked_games")
    rows = lite_cur.fetchall()
    with pg_conn.cursor() as pg_cur:
        pg_cur.execute("DELETE FROM tracked_games")
        for row in rows:
            pg_cur.execute("INSERT INTO tracked_games (guild_id, game_substring, role_suffix) VALUES (%s, %s, %s)", (DEFAULT_GUILD_ID, row[0], row[1]))
    
    print("  Processing reaction_role_messages (with default guild_id)...")
    lite_cur.execute("SELECT * FROM reaction_role_messages")
    rows = lite_cur.fetchall()
    with pg_conn.cursor() as pg_cur:
        pg_cur.execute("DELETE FROM reaction_role_messages")
        for row in rows:
            pg_cur.execute("INSERT INTO reaction_role_messages (guild_id, identifier, channel_id, message_id) VALUES (%s, %s, %s, %s)", (DEFAULT_GUILD_ID, row[0], row[1], row[2]))
    
    pg_conn.commit()
    lite_conn.close()
    pg_conn.close()
    print("Activity migration complete.")

def migrate_message_db():
    print("Migrating message archive database...")
    if not os.path.exists(SQLITE_MESSAGE_DB):
        print(f"File {SQLITE_MESSAGE_DB} not found, skipping.")
        return

    lite_conn = sqlite3.connect(SQLITE_MESSAGE_DB)
    pg_conn = psycopg2.connect(POSTGRES_URL)
    
    # 1. Messages
    print("  Processing messages...")
    lite_cur = lite_conn.cursor()
    lite_cur.execute("SELECT * FROM messages")
    with pg_conn.cursor() as pg_cur:
        pg_cur.execute("DELETE FROM messages")
        while True:
            rows = lite_cur.fetchmany(1000)
            if not rows:
                break
            pg_cur.executemany("INSERT INTO messages (message_id, guild_id, channel_id, user_id, username, content, attachments, timestamp, is_bot) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", rows)
        pg_conn.commit()

    # 2. Sync state
    print("  Processing channel_sync_state (with default guild_id)...")
    lite_cur.execute("SELECT * FROM channel_sync_state")
    rows = lite_cur.fetchall()
    with pg_conn.cursor() as pg_cur:
        pg_cur.execute("DELETE FROM channel_sync_state")
        for row in rows:
            pg_cur.execute("INSERT INTO channel_sync_state (guild_id, channel_id, oldest_message_id, is_completed) VALUES (%s, %s, %s, %s)", (DEFAULT_GUILD_ID, row[0], row[1], row[2]))
    
    pg_conn.commit()
    lite_conn.close()
    pg_conn.close()
    print("Message migration complete.")

if __name__ == "__main__":
    if not POSTGRES_URL:
        print("DATABASE_URL not set in .env!")
    else:
        migrate_activity_db()
        migrate_message_db()
