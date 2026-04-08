import discord
from core.ui_icons import Icons
from core.ui_translate import t

def get_feedback(key: str, **kwargs) -> str:
    """
    This helper function finds the right emoji for our message and adds it to the translated text!
    """
    icons_map = {
        # --- Errors (The red 'X' emoji) ---
        "error_generic": Icons.ERROR,
        "ERR_STATS_LOAD": Icons.ERROR,
        "ERR_STATS_NOT_FOUND": Icons.ERROR,
        "DB_RESET_ERROR": Icons.ERROR,
        "ERR_GENERIC": Icons.ERROR,
        "ERR_WRONG_GUILD": Icons.ERROR,
        "ERR_LAYOUT_TEST": Icons.ERROR,
        "ERR_LIMIT_REACHED": Icons.ERROR,
        "ERR_INVALID_ID": Icons.ERROR,
        "ERR_CONFIG_SAVE": Icons.ERROR,
        "RR_ERROR_ROLE_NOT_FOUND": Icons.ERROR,
        "RR_ERROR_GENERIC": Icons.ERROR,

        # --- Warnings (The yellow triangle emoji) ---
        "no_permission": Icons.WARNING,
        "admin_only": Icons.WARNING,
        "ERR_NO_DATA": Icons.WARNING,
        "ERR_NO_DATA_PERIOD": Icons.WARNING,
        "ERR_STATS_CHANNEL": Icons.WARNING,
        "ERR_ADMIN_ONLY": Icons.WARNING,
        "LB_EMPTY": Icons.WARNING,
        "GAME_LIST_EMPTY": Icons.WARNING,
        "GAME_REPORT_EMPTY": Icons.WARNING,
        "REPORT_EMPTY_HISTORY": Icons.WARNING,
        "STREAM_HISTORY_EMPTY": Icons.WARNING,
        "MEMBERSHIP_LOG_EMPTY": Icons.WARNING,
        
        # --- Cooldown (Wait a bit!) ---
        "ERR_COOLDOWN": Icons.COOLDOWN,

        # --- Success (Everything went great!) ---
        "SUCCESS_SHARED": Icons.SUCCESS,
        "GAME_ADDED": Icons.SUCCESS,
        "DB_RESET_SUCCESS": Icons.SUCCESS,
        "SUCCESS_ELITES_FORCED": Icons.SUCCESS,
        "MODAL_ALT_SUCCESS": Icons.SUCCESS,
        "CMD_CLEAR_DONE": Icons.SUCCESS,
        "GAME_REPORT_DONE": Icons.SUCCESS,
        "STREAM_HISTORY_DONE": Icons.SUCCESS,
        "MEMBERSHIP_LOG_DONE": Icons.SUCCESS,
        "RR_ROLE_ADDED": Icons.SUCCESS,
        "RR_ROLE_REMOVED": Icons.SUCCESS,

        # --- Features & UI Elements ---
        "GAME_REMOVED": Icons.TRASH,
        "RR_ERROR_ROLE_NOT_FOUND": Icons.ERROR,
        "RR_ERROR_GENERIC": Icons.ERROR,
        "GAME_LIST_TITLE": Icons.CONTROLLER,
        "LB_TITLE_WEEKLY": Icons.CHART,
        "LB_TITLE_MONTHLY": Icons.CHART,
        "LB_TITLE_ALLTIME": Icons.CHART,
        "LB_SHARED_BY": Icons.CHART,
        "PROFILE_SHARED_BY": Icons.CHART,
        "SECTION_ACTIVITY": Icons.CHART,
        "SECTION_STATS": Icons.STATS,
        "SECTION_COMMUNITY": Icons.COMMUNITY,
        "SECTION_GAMES": Icons.CONTROLLER,
        "PRESENCE_WATCHING": "🤫",
        "PRESENCE_WATCHING_PLAYERS": "🤫",
        "PRESENCE_LISTENING_VOICE": "🤫",
        "PRESENCE_TRACKING_GAMES": "🤫",
        "PRESENCE_PRAISING_ELITE": "🏆",
        "PRESENCE_TOP_GAME": "🎮",
        "PRESENCE_HELP": "🆘",
        "PRESENCE_SASSY_1": "🤫",
        "PRESENCE_SASSY_2": "🤫",
        "PRESENCE_SASSY_3": "🤫",
        "SECTION_VETERAN": Icons.VETERAN,
        "ELITES_TITLE": Icons.TROPHY,
        "ELITE_SPOTIFY": Icons.SPOTIFY,
        "ELITE_GAMER_TOTAL": Icons.GAMER,
        "ELITE_GAMER_VARIETY": Icons.VARIETY,
        "ELITE_STREAMER": Icons.STREAMER,
        "ELITE_HALL_OF_FAME": Icons.VETERAN,
        "ELITE_HALL_OF_FAME_TITLE": Icons.TROPHY,
        "ELITE_ANNOUNCEMENT_TITLE": Icons.TROPHY,
        "ELITE_MEMELORD": Icons.MEME,
        "MEDAL_1": Icons.MEDAL_1,
        "MEDAL_2": Icons.MEDAL_2,
        "MEDAL_3": Icons.MEDAL_3,

        # --- Progress & Generation (Going fast!) ---
        "REPORT_GEN_STATUS": Icons.ROCKET,
        "REPORT_GEN_ROLE": Icons.ROCKET,
        "GAME_REPORT_GEN": Icons.ROCKET,
        "STREAM_HISTORY_GEN": Icons.ROCKET,
        "MEMBERSHIP_LOG_GEN": Icons.ROCKET,
        "INFO_FEATURES_TITLE": Icons.ROCKET,

        # --- Stat Icons ---
        "STAT_SPOTIFY": Icons.SPOTIFY,
        "STAT_MEDIA": Icons.CHART,

        # --- Empty Values (These don't need emojis) ---
        "LB_TITLE_DEFAULT": "",
        "LB_UNKNOWN_USER": "",
        "LB_POINTS": "",
        "LB_FOOTER_POINTS": "",
        "BTN_WEEKLY": "",
        "BTN_MONTHLY": "",
        "BTN_ALLTIME": "",
        "BTN_MY_RANK": "",
        "BTN_SHARE": "",
        "PROFILE_RANK": "",
        "PROFILE_SUBTITLE": "",
        "STAT_TOTAL_SCORE": "",
        "STAT_DETAILS": "",
        "STAT_LAST_ACTIVE": "",
        "STAT_DAILY_AVG": "",
        "SOCIAL_FAV_ROOM": "",
        "SOCIAL_FAV_EMOJI": "",
        "SOCIAL_MAIN_TARGET": "",
        "SOCIAL_BEST_FRIEND": "",
        "SOCIAL_FAV_ROOM_STATIC": "",
        "SOCIAL_MAIN_TARGET_STATIC": "",
        "SOCIAL_BEST_FRIEND_STATIC": "",
        "REPORT_TITLE_HEADER": "",
        "REPORT_STAGE_1": "",
        "REPORT_STAGE_2": "",
        "REPORT_STAGE_NORMAL": "",
        "REPORT_INACTIVE": "",
        "REPORT_S2_RETURN": "",
        "REPORT_S1_LIMIT": "",
        "ROLE_LOG_TITLE": "",
        "ROLE_LOG_REMOVED": "",
        "ROLE_LOG_ADDED": "",
        "GAME_POP_TITLE": "",
        "GAME_POP_MONTHLY": "",
        "GAME_POP_ALLTIME": "",
        "GAME_POP_GEN": "",
        "GAME_POP_HEADER": "",
        "CMD_TOP_DESC": "",
        "CMD_TOP_TF_DESC": "",
        "CMD_ME_MEMBER_DESC": "",
        "CMD_ADD_GAME_DESC": "",
        "CMD_ADD_GAME_NAME_DESC": "",
        "CMD_ADD_GAME_SUFFIX_DESC": "",
        "CMD_REMOVE_GAME_DESC": "",
        "CMD_REMOVE_GAME_NAME_DESC": "",
        "CMD_LIST_GAMES_DESC": "",
        "CMD_GAME_REPORT_DESC": "",
        "CMD_GAME_REPORT_TF_DESC": "",
        "CMD_STATUS_REPORT_DESC": "",
        "CMD_GAME_ROLE_REPORT_DESC": "",
        "CMD_RESET_DB_DESC": "",
        "CMD_SYNC_DESC": "",
        "CMD_SYNC_MODE_DESC": "",
        "INFO_TITLE": "",
        "INFO_DESC": "",
        "INFO_FEATURES_DESC": "",
        "INFO_FOOTER": "",
        "INFO_DEV_TITLE": "",
        "INFO_DEV_PREFIX": "",
        "INFO_DEV_SLASH": "",
        "CMD_INFO_DEV_DESC": "",
        "CMD_CLEAR_HELP": "",
        "INFO_DEV_FOOTER_NOTE": "",
        "CMD_INFO_DESC": ""
    }
    
    emoji = icons_map.get(key, "")
    text = t(key, **kwargs)
    
    # If we can't find an emoji, we just use an empty space so nothing breaks!
    emoji_str = str(emoji) if emoji is not None else ""
    
    # Sometimes the message already has the emoji inside it, so we make sure not to add it twice!
    if emoji_str and emoji_str in text:
        return text
        
    if not text:
        return emoji_str.strip()
        
    return f"{emoji_str} {text}".strip()
