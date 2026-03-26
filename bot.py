import discord
from discord.ext import commands
import os
from core.logger import log
from db_manager import DBManager
from config_loader import Config
from core.game_tracker import GameTracker
from core.stats_engine import StatsEngine
from core.messages import Messages

# Set language
Messages.load_language(Config.LANGUAGE)

class CheekyBot(commands.Bot):
    def __init__(self):
        # Init Intents
        intents = discord.Intents.default()
        intents.members = True
        intents.messages = True
        intents.voice_states = True
        intents.reactions = True
        intents.message_content = True
        intents.presences = True
        
        super().__init__(command_prefix="!", intents=intents)
        
        # Initialize Core Modules
        self.db = DBManager()
        self.tracker = GameTracker(self.db, self)
        self.engine = StatsEngine(self.db)
        
        # Track voice session start times: {user_id: join_timestamp}
        self.voice_start_times = {}

    async def setup_hook(self):
        # Clear global commands from this bot identity to prevent crossover
        self.tree.clear_commands(guild=None)

        # Load Cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    log.info(f"Loaded extension: {filename}")
                except Exception as e:
                    log.error(f"Failed to load extension {filename}: {e}")

        # Extensions are loaded, manual sync required via !sync
        log.info("Extensions loaded. Use !sync to propagate slash commands.")

    # Shared Helper methods accessible from Cogs via self.bot
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
