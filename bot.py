import discord
from discord.ext import commands
import os
from core.logger import log
from db_manager import DBManager
from config_loader import Config
from core.game_tracker import GameTracker
from core.stats_engine import StatsEngine
from core.messages import Messages
from core.ui_icons import Icons
from core.ui_theme import Theme
import logging
from logging.handlers import RotatingFileHandler

# This part helps the bot draw charts even on servers that don't have a screen!
import matplotlib
try:
    matplotlib.use('Agg') # Headless fix for Linux/Debian/Headless servers
except:
    pass

# Pick the language from our settings so the bot knows hogy mit mondjon (HU/EN)
# But wait, we'll do this in the initialization to be safe

class IrisBot(commands.Bot):
    def __init__(self):
        # Tell Discord what things the bot is allowed to see (messages, voice, who is online etc.)
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.voice_states = True
        intents.reactions = True
        intents.message_content = True
        intents.presences = True
        intents.emojis_and_stickers = True
        
        super().__init__(command_prefix=Config.PREFIX, intents=intents, help_command=None)
        
        # Set up the database and the special tools for tracking games and stats
        self.db = DBManager()
        self.tracker = GameTracker(self.db, self)
        self.engine = StatsEngine(self.db, self)
        
        # A simple dictionary to remember when people joined a voice channel
        self.voice_start_times = {}
        # Tracks the current point multiplier for each person (Main ID) in voice
        self.voice_multipliers = {}

    async def setup_hook(self):
        # Initializing our asynpg database pool!
        await self.db.initialize()
        # await self.db.migrate_from_sqlite(Config.GUILD_ID)
        
        # We clear any old or double commands from Discord's memory so everything starts fresh!
        self.tree.clear_commands(guild=None)


        # Go through the 'cogs' folder and turn on every feature file we find
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    log.info(f"Loaded extension: {filename}")
                except Exception as e:
                    log.error(f"Failed to load extension {filename}: {e}")

        # We tell the admin to run the sync command so the new features actually show up on Discord!
        log.info(f"Extensions loaded. Use {Config.PREFIX}sync{Config.SUFFIX} to propagate slash commands.")



    # These are handy little shortcuts that help other parts of the bot get data quickly!
    async def get_top_data(self, guild, user=None, timeframe="alltime"):
        return await self.engine.get_leaderboard(guild, user, timeframe, self.voice_start_times)


    async def load_game_franchises(self):
        await self.tracker.load_franchises()


if __name__ == "__main__":
    try:
        # Step 1: We set up the custom icons and then load the language files!
        Icons.setup(Config)
        log.info(Messages.LOG_UI_INIT)
        
        Messages.load_language(Config.LANGUAGE)
        log.info(Messages.LOG_BOT_START)
        
        Theme.init_theme(Config)
        
        # Step 2: We check the config.json file to make sure it was filled out correctly!
        val_error = Config.validate()
        if val_error:
            log.error(f"Config Error: {val_error}")
            import sys
            sys.exit(1)
            
        # Step 3: Finally, we turn the bot on and connect to Discord!
        log.info(Messages.LOG_CONNECTING)
        bot = IrisBot()
        bot.run(Config.TOKEN)
        
    except Exception as e:
        log.critical(f"Critical error during startup: {e}", exc_info=True)
        # Fallback to stderr if logging also fails
        import traceback
        import sys
        traceback.print_exc()
        sys.exit(1)
