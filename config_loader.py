import os
import json
from dotenv import load_dotenv

# Override=True is critical on Windows/Manager setup to prevent inheriting parent’s token
load_dotenv(override=True)

class Config:
    # Get the special bot token from the .env file (shhh, it's a secret!)
    TOKEN = os.getenv("DISCORD_TOKEN")
    
    # Read all the other settings from the config.json file
    _data: dict = {}
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            _data = json.load(f)
    except Exception as e:
        print(f"Error loading config.json: {e}")

    # These are the IDs for the special roles the bot gives out
    _roles: dict = _data.get("roles", {})
    STAGE_1_ROLE_ID = _roles.get("stage_1_id", 0)
    STAGE_2_ROLE_ID = _roles.get("stage_2_id", 0)
    ADMIN_ROLE_ID = _roles.get("admin_role_id", 0)
    TESTER_ROLE_ID = _roles.get("tester_role_id", 0)
    MEMELORD_ROLE_ID = _roles.get("memelord_id", 0) # Legacy (to be removed if everything is updated)
    BASIC_MEMBER_ROLE_ID = _roles.get("basic_member_role_id", 0)
    BASIC_MEMBER_EXCLUDED_ROLES = _roles.get("basic_member_excluded_roles", [])
    
    # Advanced Champion Role definitions (Nested with IDs, Names, Colors and Announcements)
    CHAMPION_ROLES = _data.get("champion_roles", {})
    
    # Helper properties for easy ID access (backward compatibility and core use)
    SPOTIVIBE_ROLE_ID = CHAMPION_ROLES.get("spotify", {}).get("role_id", 0)
    GODGAMER_TOTAL_ROLE_ID = CHAMPION_ROLES.get("gamer_total", {}).get("role_id", 0)
    GODGAMER_VARIETY_ROLE_ID = CHAMPION_ROLES.get("gamer_variety", {}).get("role_id", 0)
    SHARING_ROLE_ID = CHAMPION_ROLES.get("streamer", {}).get("role_id", 0)
    MEMELORD_ROLE_ID = CHAMPION_ROLES.get("media", {}).get("role_id", 0)
    HALL_OF_FAMER_ROLE_ID = CHAMPION_ROLES.get("hall_of_fame", {}).get("role_id", 0)
    
    # These tell the bot where to post stats or look for admins
    _channels: dict = _data.get("channels", {})
    GUILD_ID = _channels.get("guild_id", 0)
    ADMIN_CHANNEL_ID = _channels.get("admin_id", 0)
    STATS_CHANNEL_ID = _channels.get("stats_id", 0)
    AFK_CHANNEL_ID = _channels.get("afk_id", 0)
    EXCLUDED_CHANNELS = _channels.get("excluded", [])
    
    # How many days of inactivity before someone loses a role (thresholds)
    _thresholds = _data.get("thresholds", {})
    STAGE_1_DAYS = _thresholds.get("stage_1_days", 14)
    STAGE_2_DAYS = _thresholds.get("stage_2_days", 21)
    STAGE_2_GRACE_DAYS = _thresholds.get("stage_2_grace_days", 7)
    INACTIVE_GAME_DAYS = _thresholds.get("inactive_game_days", 30)
    SOCIAL_STATS_DAYS = _thresholds.get("social_stats_days", 30)
    CHECK_INTERVAL_HOURS = _thresholds.get("check_interval_hours", 12)
    CHAMPION_WIN_THRESHOLD = _thresholds.get("champions_win_threshold", 5)
    VARIETY_MIN_MINUTES = _thresholds.get("variety_min_minutes", 30)
    BASIC_MEMBER_THRESHOLD_MINS = _thresholds.get("basic_member_time_threshold_minutes", 15)

    # How many points people get for messages and reactions
    _scoring = _data.get("scoring", {})
    POINTS_MESSAGE_BASE = _scoring.get("points_message_base", 1)
    POINTS_MESSAGE_SCALE = _scoring.get("points_message_scale", 10)
    POINTS_MESSAGE_MAX = _scoring.get("points_message_max", 100)
    POINTS_REACTION = _scoring.get("points_reaction", 5)
    POINTS_VOICE = _scoring.get("points_voice_per_min", 2)
    POINTS_STREAM_BONUS = _scoring.get("points_voice_streaming_bonus", 2)
    POINTS_MEDIA_BONUS = _scoring.get("points_media_bonus", 5)

    # Settings for how the bot looks and how much data it shows
    _ui = _data.get("ui", {})
    PREFIX = _ui.get("prefix", "!")
    SUFFIX = _ui.get("suffix", "")
    LEADERBOARD_LIMIT = _ui.get("leaderboard_limit", 10)
    REPORT_LOG_LIMIT = _ui.get("report_log_limit", 300)
    DEFAULT_GAMES = _ui.get("default_games", {})
    RECENT_GAMES_LIMIT = _ui.get("recent_games_limit", 3)
    LANGUAGE = _ui.get("language", "hu")
    GAME_ROLE_PREFIX = _ui.get("game_role_prefix", "Player: ")
    PRESENCE_ROTATION_MINUTES = _ui.get("presence_rotation_minutes", 5)
    PRESENCE_ROTATION = _ui.get("presence_rotation", ["stats", "sassy", "help"])
    
    # New UI settings for color and emoji customization
    THEME = _ui.get("theme", {})
    EMOJIS = _data.get("emojis", {})
    
    # Backward compatibility for these two specific colors
    COLOR_PRIMARY = int(str(_ui.get("color_primary", "0x3498db")), 16)
    COLOR_SUCCESS = int(str(_ui.get("color_success", "0x2ecc71")), 16)
    COLOR_WARNING = int(str(_ui.get("color_warning", "0xFEE75C")), 16)
    COLOR_DANGER = int(str(_ui.get("color_danger", "0xED4245")), 16)
    COLOR_ACCENT = int(str(_ui.get("color_accent", "0xEB459E")), 16)
    DEFAULT_STREAM_NAME = _ui.get("default_stream_name", "Screen")

    # Patterns for media detection (YouTube, TikTok, images, etc.)
    _media = _data.get("media", {})
    MEDIA_PATTERNS = _media.get("patterns", [
        r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|tiktok\.com|imgur\.com|instagram\.com|giphy\.com|media\.giphy\.com|tenor\.com|fb\.watch|facebook\.com|fbcdn\.net)/[^\s]+",
        r"https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|mp4|webm|mov)(?:\?[^\s]+)?"
    ])

    # This part helps the bot know if two Discord accounts belong to the same person
    _user_mapping = _data.get("user_mapping", {})
    # This turns the list into numbers so the computer can understand it better
    USER_MAPPING = {int(k): int(v) for k, v in _user_mapping.items()}

    @classmethod
    def get_main_id(cls, user_id):
        """Returns the main account ID if the user is an alt, otherwise returns the user_id itself."""
        return cls.USER_MAPPING.get(user_id, user_id)

    @classmethod
    def update_user_mapping(cls, alt_id: int, main_id: int):
        """Adds or updates an alt-to-main account mapping and persists it to config.json."""
        # Update in-memory mapping
        cls.USER_MAPPING[alt_id] = main_id
        
        # Update the original _data for future saves (if any)
        if "user_mapping" not in cls._data:
            cls._data["user_mapping"] = {}
        cls._data["user_mapping"][str(alt_id)] = main_id
        
        # Persist to config.json
        try:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(cls._data, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config.json: {e}")
            return False

    @classmethod
    def validate(cls):
        if not cls.TOKEN:
            return "DISCORD_TOKEN is missing from .env"
        if cls.STAGE_1_ROLE_ID == 0 or cls.STAGE_2_ROLE_ID == 0:
            return "Role IDs are not set in config.json"
        return None

    @classmethod
    def format_desc(cls, text: str, guild=None) -> str:
        """Fills placeholders in command descriptions with current config values or names."""
        if not text: return text
        
        admin_val = str(cls.ADMIN_CHANNEL_ID)
        stats_val = str(cls.STATS_CHANNEL_ID)
        role_val = str(cls.ADMIN_ROLE_ID)

        if guild:
            # Resolve channel names
            admin_ch = guild.get_channel(cls.ADMIN_CHANNEL_ID)
            if admin_ch: admin_val = admin_ch.name
            
            stats_ch = guild.get_channel(cls.STATS_CHANNEL_ID)
            if stats_ch: stats_val = stats_ch.name

            # Resolve role name
            role_obj = guild.get_role(cls.ADMIN_ROLE_ID)
            if role_obj: role_val = role_obj.name

        return text.format(
            admin_id=admin_val,
            stats_id=stats_val,
            role_id=role_val,
            prefix=cls.PREFIX,
            suffix=cls.SUFFIX,
            bot_name="Activity Watcher"
        )
