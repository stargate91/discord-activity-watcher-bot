import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    TOKEN = os.getenv("DISCORD_TOKEN")
    STAGE_1_ROLE_ID = int(os.getenv("STAGE_1_ROLE_ID", "0"))
    STAGE_2_ROLE_ID = int(os.getenv("STAGE_2_ROLE_ID", "0"))
    ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID", "0"))
    AFK_CHANNEL_ID = int(os.getenv("AFK_CHANNEL_ID", "1275929869703970876"))
    
    # Thresholds in days

    STAGE_1_DAYS = int(os.getenv("STAGE_1_DAYS", "14")) # default 2 weeks
    STAGE_2_DAYS = int(os.getenv("STAGE_2_DAYS", "21")) # default 3 weeks (if they have role 1)
    
    CHECK_INTERVAL_HOURS = int(os.getenv("CHECK_INTERVAL_HOURS", "12")) # How often to check all users

    @classmethod
    def validate(cls):
        if not cls.TOKEN:
            return "DISCORD_TOKEN is missing from .env"
        if cls.STAGE_1_ROLE_ID == 0 or cls.STAGE_2_ROLE_ID == 0:
            return "Role IDs are not set in .env"
        return None
