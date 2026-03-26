import os
from dotenv import load_dotenv

# Override=True is critical on Windows/Manager setup to prevent inheriting parent’s token
load_dotenv(override=True)

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    STAGE_1_ROLE_ID = int(os.getenv("STAGE_1_ROLE_ID", "0"))
    STAGE_2_ROLE_ID = int(os.getenv("STAGE_2_ROLE_ID", "0"))
    ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
    GUILD_ID = int(os.getenv("GUILD_ID", "1083433370815582240"))
    AFK_CHANNEL_ID = int(os.getenv("AFK_CHANNEL_ID", "1275929869703970876"))
    STATS_CHANNEL_ID = int(os.getenv("STATS_CHANNEL_ID", "0"))
    
    # Thresholds in days

    STAGE_1_DAYS = int(os.getenv("STAGE_1_DAYS", "14")) # default 2 weeks
    STAGE_2_DAYS = int(os.getenv("STAGE_2_DAYS", "21")) # default 3 weeks (if they have role 1)
    STAGE_2_GRACE_DAYS = int(os.getenv("STAGE_2_GRACE_DAYS", "7")) # how many days of activity needed to lose stage 2
    INACTIVE_GAME_DAYS = int(os.getenv("INACTIVE_GAME_DAYS", "30")) # remove game role after this many days of inactivity
    SOCIAL_STATS_DAYS = int(os.getenv("SOCIAL_STATS_DAYS", "30")) # lookback for favorites/averages
    
    CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "12")) # How often to check all users
    
    EXCLUDED_CHANNELS = [int(i.strip()) for i in os.getenv("EXCLUDED_CHANNELS", "").split(",") if i.strip()]

    # Scoring System
    POINTS_MESSAGE = int(os.getenv("POINTS_MESSAGE", "10"))
    POINTS_REACTION = int(os.getenv("POINTS_REACTION", "5"))
    POINTS_VOICE = int(os.getenv("POINTS_VOICE", "2")) # per minute

    # UI & Limits
    LEADERBOARD_LIMIT = int(os.getenv("LEADERBOARD_LIMIT", "10"))
    REPORT_LOG_LIMIT = int(os.getenv("REPORT_LOG_LIMIT", "300"))
    COLOR_PRIMARY = int(os.getenv("COLOR_PRIMARY", "0x3498db"), 16) # discord.Color.blue()
    COLOR_SUCCESS = int(os.getenv("COLOR_SUCCESS", "0x2ecc71"), 16) # discord.Color.green()
    RECENT_GAMES_LIMIT = int(os.getenv("RECENT_GAMES_LIMIT", "3"))

    @classmethod
    def validate(cls):
        if not cls.TOKEN:
            return "DISCORD_TOKEN is missing from .env"
        if cls.STAGE_1_ROLE_ID == 0 or cls.STAGE_2_ROLE_ID == 0:
            return "Role IDs are not set in .env"
        return None
