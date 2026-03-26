import os
import json
from dotenv import load_dotenv

# Override=True is critical on Windows/Manager setup to prevent inheriting parent’s token
load_dotenv(override=True)

class Config:
    # Secret
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    # Load JSON Config
    _data = {}
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            _data = json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")

    # Role IDs
    _roles = _data.get("roles", {})
    STAGE_1_ROLE_ID = _roles.get("stage_1_id", 0)
    STAGE_2_ROLE_ID = _roles.get("stage_2_id", 0)
    
    # Channel IDs
    _channels = _data.get("channels", {})
    GUILD_ID = _channels.get("guild_id", 0)
    ADMIN_CHANNEL_ID = _channels.get("admin_id", 0)
    STATS_CHANNEL_ID = _channels.get("stats_id", 0)
    AFK_CHANNEL_ID = _channels.get("afk_id", 0)
    EXCLUDED_CHANNELS = _channels.get("excluded", [])
    
    # Thresholds
    _thresholds = _data.get("thresholds", {})
    STAGE_1_DAYS = _thresholds.get("stage_1_days", 14)
    STAGE_2_DAYS = _thresholds.get("stage_2_days", 21)
    STAGE_2_GRACE_DAYS = _thresholds.get("stage_2_grace_days", 7)
    INACTIVE_GAME_DAYS = _thresholds.get("inactive_game_days", 30)
    SOCIAL_STATS_DAYS = _thresholds.get("social_stats_days", 30)
    CHECK_INTERVAL_HOURS = _thresholds.get("check_interval_hours", 12)

    # Scoring
    _scoring = _data.get("scoring", {})
    POINTS_MESSAGE = _scoring.get("points_message", 10)
    POINTS_REACTION = _scoring.get("points_reaction", 5)
    POINTS_VOICE = _scoring.get("points_voice_per_min", 2)

    # UI & Limits
    _ui = _data.get("ui", {})
    LEADERBOARD_LIMIT = _ui.get("leaderboard_limit", 10)
    REPORT_LOG_LIMIT = _ui.get("report_log_limit", 300)
    COLOR_PRIMARY = int(_ui.get("color_primary", "0x3498db"), 16)
    COLOR_SUCCESS = int(_ui.get("color_success", "0x2ecc71"), 16)
    RECENT_GAMES_LIMIT = _ui.get("recent_games_limit", 3)

    @classmethod
    def validate(cls):
        if not cls.TOKEN:
            return "DISCORD_TOKEN is missing from .env"
        if cls.STAGE_1_ROLE_ID == 0 or cls.STAGE_2_ROLE_ID == 0:
            return "Role IDs are not set in config.json"
        return None
