from core.ui_translate import t, set_language, load_locales
from core.ui_utils import get_feedback

class Messages:
    # --- Performance Titles ---
    LB_TITLE_WEEKLY = ""
    LB_TITLE_MONTHLY = ""
    LB_TITLE_ALLTIME = ""
    LB_TITLE_DEFAULT = ""
    LB_SHARED_BY = ""
    LB_EMPTY = ""
    LB_UNKNOWN_USER = ""
    LB_POINTS = ""
    LB_FOOTER_POINTS = ""
    
    # --- Interactive Components ---
    BTN_WEEKLY = ""
    BTN_MONTHLY = ""
    BTN_ALLTIME = ""
    BTN_MY_RANK = ""
    BTN_SHARE = ""
    
    # --- Profile Sections ---
    PROFILE_SHARED_BY = ""
    PROFILE_RANK = ""
    PROFILE_SUBTITLE = ""
    SECTION_ACTIVITY = ""
    SECTION_STATS = ""
    SECTION_COMMUNITY = ""
    SECTION_GAMES = ""
    STAT_TOTAL_SCORE = ""
    STAT_DETAILS = ""
    STAT_LAST_ACTIVE = ""
    STAT_DAILY_AVG = ""
    STAT_MEDIA = ""
    
    # --- Social Connections ---
    SOCIAL_FAV_ROOM = ""
    SOCIAL_FAV_EMOJI = ""
    SOCIAL_MAIN_TARGET = ""
    SOCIAL_BEST_FRIEND = ""
    SOCIAL_FAV_ROOM_STATIC = ""
    SOCIAL_MAIN_TARGET_STATIC = ""
    SOCIAL_BEST_FRIEND_STATIC = ""
    
    # --- System Errors & Messages ---
    ERR_NO_DATA = ""
    ERR_NO_DATA_PERIOD = ""
    ERR_STATS_CHANNEL = ""
    ERR_ADMIN_ONLY = ""
    SUCCESS_SHARED = ""
    REPORT_GEN_STATUS = ""
    REPORT_GEN_ROLE = ""
    REPORT_EMPTY_HISTORY = ""
    
    # --- Game Management ---
    GAME_ADDED = ""
    GAME_REMOVED = ""
    GAME_LIST_EMPTY = ""
    GAME_LIST_TITLE = ""
    GAME_REPORT_GEN = ""
    GAME_REPORT_EMPTY = ""
    GAME_REPORT_DONE = ""
    DB_RESET_SUCCESS = ""
    DB_RESET_ERROR = ""
    
    # --- Logging & Reports ---
    REPORT_TITLE_HEADER = ""
    REPORT_STAGE_1 = ""
    REPORT_STAGE_2 = ""
    REPORT_STAGE_NORMAL = ""
    REPORT_INACTIVE = ""
    REPORT_S2_RETURN = ""
    REPORT_S1_LIMIT = ""
    ROLE_LOG_TITLE = ""
    ROLE_LOG_REMOVED = ""
    ROLE_LOG_ADDED = ""
    GAME_POP_TITLE = ""
    GAME_POP_MONTHLY = ""
    GAME_POP_ALLTIME = ""
    GAME_POP_GEN = ""
    GAME_POP_HEADER = ""
    PRESENCE_WATCHING = ""
    
    # --- Command Descriptions ---
    CMD_TOP_DESC = ""
    CMD_TOP_TF_DESC = ""
    CMD_ME_MEMBER_DESC = ""
    CMD_ADD_GAME_DESC = ""
    CMD_ADD_GAME_NAME_DESC = ""
    CMD_ADD_GAME_SUFFIX_DESC = ""
    CMD_REMOVE_GAME_DESC = ""
    CMD_REMOVE_GAME_NAME_DESC = ""
    CMD_LIST_GAMES_DESC = ""
    CMD_GAME_REPORT_DESC = ""
    CMD_GAME_REPORT_TF_DESC = ""
    CMD_GAME_DETAILS_DESC = ""
    CMD_GAME_DETAILS_GAME_DESC = ""
    GAME_DETAILS_TITLE = ""
    GAME_DETAILS_HEADER = ""
    CMD_STATUS_REPORT_DESC = ""
    CMD_GAME_ROLE_REPORT_DESC = ""
    CMD_RESET_DB_DESC = ""
    CMD_SYNC_DESC = ""
    CMD_SYNC_MODE_DESC = ""
    CMD_INFO_DEV_DESC = ""
    CMD_INFO_DESC = ""
    CMD_CLEAR_HELP = ""
    CMD_CLEAR_DONE = ""
    CMD_SERVER_ANALYSIS_DESC = ""
    CMD_SERVER_ANALYSIS_TYPE_DESC = ""
    CMD_SERVER_ANALYSIS_TF_DESC = ""
    CHART_PEAK_TITLE = ""
    CHART_VOICE_TITLE = ""
    CHART_X_HOUR = ""
    CHART_Y_DAY = ""
    CHART_Y_MINUTES = ""
    DAY_0 = ""
    DAY_1 = ""
    DAY_2 = ""
    DAY_3 = ""
    DAY_4 = ""
    DAY_5 = ""
    DAY_6 = ""
    STAT_AVG_VOICE = ""
    CHART_DEDICATION_TITLE = ""
    CHART_X_MIN_SESSION = ""
    CHART_CHANNEL_TITLE = ""
    CHART_Y_MESSAGES = ""
    
    # --- General Information ---
    INFO_TITLE = ""
    INFO_DESC = ""
    INFO_FEATURES_TITLE = ""
    INFO_FEATURES_DESC = ""
    INFO_FOOTER = ""
    INFO_DEV_TITLE = ""
    INFO_DEV_PREFIX = ""
    INFO_DEV_SLASH = ""
    INFO_DEV_FOOTER_NOTE = ""
    
    # --- Specialized Errors ---
    ERR_STATS_LOAD = ""
    ERR_STATS_NOT_FOUND = ""

    @classmethod
    def load_language(cls, lang_code):
        """This now bridges the old attribute-based access with the new JSON locales."""
        # Ensure locales are loaded
        load_locales()
        set_language(lang_code)
        
        # This list must match all attributes defined above exactly
        keys = (
            "LB_TITLE_WEEKLY", "LB_TITLE_MONTHLY", "LB_TITLE_ALLTIME", "LB_TITLE_DEFAULT", 
            "LB_SHARED_BY", "LB_EMPTY", "LB_UNKNOWN_USER", "LB_POINTS", "LB_FOOTER_POINTS",
            "BTN_WEEKLY", "BTN_MONTHLY", "BTN_ALLTIME", "BTN_MY_RANK", "BTN_SHARE",
            "PROFILE_SHARED_BY", "PROFILE_RANK", "PROFILE_SUBTITLE", "SECTION_ACTIVITY", 
            "SECTION_STATS", "SECTION_COMMUNITY", "SECTION_GAMES", "STAT_TOTAL_SCORE", 
            "STAT_DETAILS", "STAT_LAST_ACTIVE", "STAT_DAILY_AVG", "SOCIAL_FAV_ROOM", 
            "SOCIAL_FAV_EMOJI", "SOCIAL_MAIN_TARGET", "SOCIAL_BEST_FRIEND", 
            "SOCIAL_FAV_ROOM_STATIC", "SOCIAL_MAIN_TARGET_STATIC", "SOCIAL_BEST_FRIEND_STATIC",
            "STAT_MEDIA", "STAT_SPOTIFY",
            "ERR_NO_DATA", "ERR_NO_DATA_PERIOD", "ERR_STATS_CHANNEL", "ERR_ADMIN_ONLY", 
            "SUCCESS_SHARED", "REPORT_GEN_STATUS", "REPORT_GEN_ROLE", "REPORT_EMPTY_HISTORY",
            "GAME_ADDED", "GAME_REMOVED", "GAME_LIST_EMPTY", "GAME_LIST_TITLE", 
            "GAME_REPORT_GEN", "GAME_REPORT_EMPTY", "GAME_REPORT_DONE", "DB_RESET_SUCCESS", 
            "DB_RESET_ERROR", "REPORT_TITLE_HEADER", "REPORT_STAGE_1", "REPORT_STAGE_2", 
            "REPORT_STAGE_NORMAL", "REPORT_INACTIVE", "REPORT_S2_RETURN", "REPORT_S1_LIMIT", 
            "ROLE_LOG_TITLE", "ROLE_LOG_REMOVED", "ROLE_LOG_ADDED", "GAME_POP_TITLE", 
            "GAME_POP_MONTHLY", "GAME_POP_ALLTIME", "GAME_POP_GEN", "GAME_POP_HEADER", 
            "PRESENCE_WATCHING", "CMD_TOP_DESC", "CMD_TOP_TF_DESC", "CMD_ME_MEMBER_DESC", 
            "CMD_ADD_GAME_DESC", "CMD_ADD_GAME_NAME_DESC", "CMD_ADD_GAME_SUFFIX_DESC", 
            "CMD_REMOVE_GAME_DESC", "CMD_REMOVE_GAME_NAME_DESC", "CMD_LIST_GAMES_DESC", 
            "CMD_GAME_REPORT_DESC", "CMD_GAME_REPORT_TF_DESC", 
            "CMD_GAME_DETAILS_DESC", "CMD_GAME_DETAILS_GAME_DESC", "GAME_DETAILS_TITLE", "GAME_DETAILS_HEADER",
            "CMD_STATUS_REPORT_DESC", 
            "CMD_GAME_ROLE_REPORT_DESC", "CMD_RESET_DB_DESC", "CMD_SYNC_DESC", "CMD_SYNC_MODE_DESC", 
            "CMD_INFO_DEV_DESC", "CMD_INFO_DESC", "CMD_CLEAR_HELP", "CMD_CLEAR_DONE", 
            "CMD_SERVER_ANALYSIS_DESC", "CMD_SERVER_ANALYSIS_TYPE_DESC", "CMD_SERVER_ANALYSIS_TF_DESC",
            "CHART_PEAK_TITLE", "CHART_VOICE_TITLE", "CHART_X_HOUR", "CHART_Y_DAY", "CHART_Y_MINUTES",
            "DAY_0", "DAY_1", "DAY_2", "DAY_3", "DAY_4", "DAY_5", "DAY_6",
            "STAT_AVG_VOICE", "CHART_DEDICATION_TITLE", "CHART_X_MIN_SESSION",
            "CHART_CHANNEL_TITLE", "CHART_Y_MESSAGES",
            "INFO_TITLE", 
            "INFO_DESC", "INFO_FEATURES_TITLE", "INFO_FEATURES_DESC", "INFO_FOOTER", 
            "INFO_DEV_TITLE", "INFO_DEV_PREFIX", "INFO_DEV_SLASH", "INFO_DEV_FOOTER_NOTE",
            "ERR_STATS_LOAD", "ERR_STATS_NOT_FOUND",
            "CMD_STREAM_HISTORY_DESC", "CMD_STREAM_HISTORY_DAYS_DESC", "STREAM_HISTORY_GEN", "STREAM_HISTORY_EMPTY", "STREAM_HISTORY_DONE",
            "SECTION_VETERAN", "STAT_JOIN_DATE", "STAT_TENURE", "STAT_LOYALTY", "CMD_MEMBERSHIP_LOGS_DESC",
            "MEMBERSHIP_LOG_GEN", "MEMBERSHIP_LOG_EMPTY", "MEMBERSHIP_LOG_DONE",
            "CHAMPIONS_TITLE", "CHAMPIONS_FOOTER", "CHAMPION_SPOTIFY", "CHAMPION_GAMER_TOTAL", "CHAMPION_GAMER_VARIETY", "CHAMPION_STREAMER", "CHAMPION_HALL_OF_FAME"
        )
        
        for key in keys:
            setattr(cls, key, get_feedback(key))

    @classmethod
    def get_lb_title(cls, timeframe):
        return {
            "weekly": cls.LB_TITLE_WEEKLY,
            "monthly": cls.LB_TITLE_MONTHLY,
            "alltime": cls.LB_TITLE_ALLTIME
        }.get(timeframe.lower(), cls.LB_TITLE_DEFAULT)
