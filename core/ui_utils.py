import discord
from core.ui_icons import Icons
from core.ui_translate import t

def get_feedback(key: str, **kwargs) -> str:
    """
    Returns a translated string prefixed with the appropriate emoji.
    """
    icons_map = {
        # --- Errors & Warnings ---
        "no_permission": Icons.WARNING,
        "admin_only": Icons.WARNING,
        "error_generic": Icons.ERROR,
        "ERR_NO_DATA": Icons.WARNING,
        "ERR_NO_DATA_PERIOD": Icons.WARNING,
        "ERR_STATS_CHANNEL": Icons.WARNING,
        "ERR_ADMIN_ONLY": Icons.WARNING,
        "ERR_STATS_LOAD": Icons.ERROR,
        "ERR_STATS_NOT_FOUND": Icons.ERROR,
        "DB_RESET_ERROR": Icons.ERROR,

        # --- Success ---
        "SUCCESS_SHARED": Icons.SUCCESS,
        "GAME_ADDED": Icons.SUCCESS,
        "DB_RESET_SUCCESS": Icons.SUCCESS,
        "CMD_CLEAR_DONE": Icons.SUCCESS,

        # --- Features & Status ---
        "GAME_REMOVED": Icons.TRASH,
        "GAME_LIST_TITLE": Icons.CONTROLLER,
        "GAME_REPORT_DONE": Icons.CHART,
        "LB_TITLE_WEEKLY": Icons.CHART,
        "LB_TITLE_MONTHLY": Icons.CHART,
        "LB_TITLE_ALLTIME": Icons.CHART,
        "LB_SHARED_BY": Icons.CHART,
        "LB_EMPTY": Icons.ROCKET,
        "PROFILE_SHARED_BY": Icons.CHART,
        "SECTION_ACTIVITY": Icons.CHART,
        "SECTION_STATS": Icons.STATS,
        "SECTION_COMMUNITY": Icons.COMMUNITY,
        "SECTION_GAMES": Icons.CONTROLLER,
        "PRESENCE_WATCHING": Icons.SHUSH,
        "INFO_FEATURES_TITLE": Icons.ROCKET,

        # --- Others (No Emoji yet) ---
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
        "REPORT_GEN_STATUS": "",
        "REPORT_GEN_ROLE": "",
        "REPORT_EMPTY_HISTORY": "",
        "GAME_LIST_EMPTY": "",
        "GAME_REPORT_GEN": "",
        "GAME_REPORT_EMPTY": "",
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
    
    # If emoji is None (failed load), use empty string
    emoji_str = str(emoji) if emoji is not None else ""
    
    # If the text already contains the emoji (manual placeholder in JSON), don't double it
    if emoji_str and emoji_str in text:
        return text
        
    if not text:
        return emoji_str.strip()
        
    return f"{emoji_str} {text}".strip()
