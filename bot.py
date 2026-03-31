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

# Set up the UI icons and theme before loading any messages
Icons.setup(Config)
Theme.init_theme(Config)

# Pick the language from our settings so the bot knows how to talk (HU/EN)
Messages.load_language(Config.LANGUAGE)

class CheekyBot(commands.Bot):
    def __init__(self):
        # Tell Discord what things the bot is allowed to see (messages, voice, who is online etc.)
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.voice_states = True
        intents.reactions = True
        intents.message_content = True
        intents.presences = True
        
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
        # Make sure we don't have old or double commands hanging around on Discord
        self.tree.clear_commands(guild=None)

        # Go through the 'cogs' folder and turn on every feature file we find
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    log.info(f"Loaded extension: {filename}")
                except Exception as e:
                    log.error(f"Failed to load extension {filename}: {e}")

        # Remind the admin to sync the commands so they actually show up in Discord
        log.info(f"Extensions loaded. Use {Config.PREFIX}sync{Config.SUFFIX} to propagate slash commands.")

        # One-time migration for voice overlaps cache
        self.db.migrate_voice_overlaps()

    # These are shortcut functions that other parts of the bot can use easily
    def get_top_data(self, guild, user=None, timeframe="alltime"):
        return self.engine.get_leaderboard(guild, user, timeframe, self.voice_start_times)

    async def load_game_franchises(self):
        await self.tracker.load_franchises()

    async def migrate_role_logs(self):
        await self.tracker.migrate_role_logs(self)

bot = CheekyBot()

if __name__ == "__main__":
    if Config.validate() is None: 
        bot.run(Config.TOKEN)
    else: 
        log.error(f"Config Error: {Config.validate()}")
