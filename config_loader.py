import os
import json
import discord
from dotenv import load_dotenv

# We use override=True to make sure the computer uses the right token for this bot!
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
    CHAMPION_EXCLUDE_ROLE_ID = _roles.get("champion_exclude_role_id", 0)
    
    # Here are all the special settings for the champion roles, like their colors and names.
    CHAMPION_ROLES = _data.get("champion_roles", {})
    
    # These are shortcuts so we can quickly find the ID for each champion role.
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
    EMOJI_CHANNEL_ID = _channels.get("emoji_id", 0)
    
    # We set these numbers to decide when someone has been away for too long.
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
    REACTION_ROLES = _data.get("reaction_roles", [])
    WELCOME = _data.get("welcome", {})
    LOGGING = _data.get("logging", {})
    
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
    def reload(cls):
        """This function reloads all our settings so the bot knows about any changes we made to config.json!"""
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cls._data = json.load(f)
            
            # Re-initialize all class attributes
            cls._roles = cls._data.get("roles", {})
            cls.STAGE_1_ROLE_ID = cls._roles.get("stage_1_id", 0)
            cls.STAGE_2_ROLE_ID = cls._roles.get("stage_2_id", 0)
            cls.ADMIN_ROLE_ID = cls._roles.get("admin_role_id", 0)
            cls.TESTER_ROLE_ID = cls._roles.get("tester_role_id", 0)
            cls.MEMELORD_ROLE_ID = cls._roles.get("memelord_id", 0)
            cls.BASIC_MEMBER_ROLE_ID = cls._roles.get("basic_member_role_id", 0)
            cls.BASIC_MEMBER_EXCLUDED_ROLES = cls._roles.get("basic_member_excluded_roles", [])
            cls.CHAMPION_EXCLUDE_ROLE_ID = cls._roles.get("champion_exclude_role_id", 0)
            
            cls.CHAMPION_ROLES = cls._data.get("champion_roles", {})
            cls.SPOTIVIBE_ROLE_ID = cls.CHAMPION_ROLES.get("spotify", {}).get("role_id", 0)
            cls.GODGAMER_TOTAL_ROLE_ID = cls.CHAMPION_ROLES.get("gamer_total", {}).get("role_id", 0)
            cls.GODGAMER_VARIETY_ROLE_ID = cls.CHAMPION_ROLES.get("gamer_variety", {}).get("role_id", 0)
            cls.SHARING_ROLE_ID = cls.CHAMPION_ROLES.get("streamer", {}).get("role_id", 0)
            cls.MEMELORD_ROLE_ID = cls.CHAMPION_ROLES.get("media", {}).get("role_id", 0)
            cls.HALL_OF_FAMER_ROLE_ID = cls.CHAMPION_ROLES.get("hall_of_fame", {}).get("role_id", 0)
            
            cls._channels = cls._data.get("channels", {})
            cls.GUILD_ID = cls._channels.get("guild_id", 0)
            cls.ADMIN_CHANNEL_ID = cls._channels.get("admin_id", 0)
            cls.STATS_CHANNEL_ID = cls._channels.get("stats_id", 0)
            cls.AFK_CHANNEL_ID = cls._channels.get("afk_id", 0)
            cls.EXCLUDED_CHANNELS = cls._channels.get("excluded", [])
            cls.EMOJI_CHANNEL_ID = cls._channels.get("emoji_id", 0)
            
            cls._thresholds = cls._data.get("thresholds", {})
            cls.STAGE_1_DAYS = cls._thresholds.get("stage_1_days", 14)
            cls.STAGE_2_DAYS = cls._thresholds.get("stage_2_days", 21)
            cls.STAGE_2_GRACE_DAYS = cls._thresholds.get("stage_2_grace_days", 7)
            cls.INACTIVE_GAME_DAYS = cls._thresholds.get("inactive_game_days", 30)
            cls.SOCIAL_STATS_DAYS = cls._thresholds.get("social_stats_days", 30)
            cls.CHECK_INTERVAL_HOURS = cls._thresholds.get("check_interval_hours", 12)
            cls.CHAMPION_WIN_THRESHOLD = cls._thresholds.get("champions_win_threshold", 5)
            cls.VARIETY_MIN_MINUTES = cls._thresholds.get("variety_min_minutes", 30)
            cls.BASIC_MEMBER_THRESHOLD_MINS = cls._thresholds.get("basic_member_time_threshold_minutes", 15)

            cls._scoring = cls._data.get("scoring", {})
            cls.POINTS_MESSAGE_BASE = cls._scoring.get("points_message_base", 1)
            cls.POINTS_MESSAGE_SCALE = cls._scoring.get("points_message_scale", 10)
            cls.POINTS_MESSAGE_MAX = cls._scoring.get("points_message_max", 100)
            cls.POINTS_REACTION = cls._scoring.get("points_reaction", 5)
            cls.POINTS_VOICE = cls._scoring.get("points_voice_per_min", 2)
            cls.POINTS_STREAM_BONUS = cls._scoring.get("points_voice_streaming_bonus", 2)
            cls.POINTS_MEDIA_BONUS = cls._scoring.get("points_media_bonus", 5)

            cls._ui = cls._data.get("ui", {})
            cls.PREFIX = cls._ui.get("prefix", "!")
            cls.SUFFIX = cls._ui.get("suffix", "")
            cls.LEADERBOARD_LIMIT = cls._ui.get("leaderboard_limit", 10)
            cls.REPORT_LOG_LIMIT = cls._ui.get("report_log_limit", 300)
            cls.DEFAULT_GAMES = cls._ui.get("default_games", {})
            cls.RECENT_GAMES_LIMIT = cls._ui.get("recent_games_limit", 3)
            cls.LANGUAGE = cls._ui.get("language", "hu")
            cls.GAME_ROLE_PREFIX = cls._ui.get("game_role_prefix", "Player: ")
            cls.PRESENCE_ROTATION_MINUTES = cls._ui.get("presence_rotation_minutes", 5)
            cls.PRESENCE_ROTATION = cls._ui.get("presence_rotation", ["stats", "sassy", "help"])
            
            cls.THEME = cls._ui.get("theme", {})
            cls.EMOJIS = cls._data.get("emojis", {})
            cls.REACTION_ROLES = cls._data.get("reaction_roles", [])
            cls.WELCOME = cls._data.get("welcome", {})
            cls.LOGGING = cls._data.get("logging", {})
            
            cls.COLOR_PRIMARY = int(str(cls._ui.get("color_primary", "0x3498db")), 16)
            cls.COLOR_SUCCESS = int(str(cls._ui.get("color_success", "0x2ecc71")), 16)
            cls.COLOR_WARNING = int(str(cls._ui.get("color_warning", "0xFEE75C")), 16)
            cls.COLOR_DANGER = int(str(cls._ui.get("color_danger", "0xED4245")), 16)
            cls.COLOR_ACCENT = int(str(cls._ui.get("color_accent", "0xEB459E")), 16)
            cls.DEFAULT_STREAM_NAME = cls._ui.get("default_stream_name", "Screen")

            cls._media = cls._data.get("media", {})
            cls.MEDIA_PATTERNS = cls._media.get("patterns", [
                r"https?://(?:www\.)?(?:youtube\.com|youtu\.be|tiktok\.com|imgur\.com|instagram\.com|giphy\.com|media\.giphy\.com|tenor\.com|fb\.watch|facebook\.com|fbcdn\.net)/[^\s]+",
                r"https?://[^\s]+\.(?:jpg|jpeg|png|gif|webp|mp4|webm|mov)(?:\?[^\s]+)?"
            ])

            cls._user_mapping = cls._data.get("user_mapping", {})
            cls.USER_MAPPING = {int(k): int(v) for k, v in cls._user_mapping.items()}

            return True
        except Exception as e:
            print(f"Error reloading config.json: {e}")
            return False

    @classmethod
    def get_main_id(cls, user_id):
        """This helps the bot know if an account is an 'alt' and who the 'main' person is!"""
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
    def format_desc(cls, text: str, guild: discord.Guild = None, bot_name: str = "Iris"):
        """This is a cool trick to replace things like {admin_id} with real names in our messages!"""
        if not text: return text
        
        admin_val = str(cls.ADMIN_CHANNEL_ID)
        stats_val = str(cls.STATS_CHANNEL_ID)
        role_val = str(cls.ADMIN_ROLE_ID)
        
        if guild:
            admin_obj = guild.get_channel(cls.ADMIN_CHANNEL_ID)
            if admin_obj: admin_val = admin_obj.name
            
            stats_obj = guild.get_channel(cls.STATS_CHANNEL_ID)
            if stats_obj: stats_val = stats_obj.name
            
            role_obj = guild.get_role(cls.ADMIN_ROLE_ID)
            if role_obj: role_val = role_obj.name

        return text.format(
            admin_id=admin_val,
            stats_id=stats_val,
            role_id=role_val,
            prefix=cls.PREFIX,
            suffix=cls.SUFFIX,
            bot_name=bot_name
        )
