import discord
from discord.ext import commands
import os
from core.logger import log
from db_manager import DBManager
from config_loader import Config
from core.game_tracker import GameTracker
from core.stats_engine import StatsEngine

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
        self.tracker = GameTracker(self.db)
        self.engine = StatsEngine(self.db)
        
        # Track voice session start times: {user_id: join_timestamp}
        self.voice_start_times = {}

    async def setup_hook(self):
        # Clear global commands from this bot identity to prevent crossover
        self.tree.clear_commands(guild=None)

        # Load Cogs
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    log.info(f"Loaded extension: {filename}")
                except Exception as e:
                    log.error(f"Failed to load extension {filename}: {e}")

        # Sync Slash Commands
        if Config.GUILD_ID:
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Slash commands synced to guild {Config.GUILD_ID} (Instant).")
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally.")

    # Shared Helper methods accessible from Cogs via self.bot
    def get_top_data(self, guild, user=None, timeframe="alltime"):
        return self.engine.get_leaderboard(guild, user, timeframe, self.voice_start_times)

    async def load_game_franchises(self):
        await self.tracker.load_franchises()

    async def migrate_role_logs(self):
        await self.tracker.migrate_role_logs(self)

bot = CheekyBot()

if __name__ == "__main__":
    if not Config.validate(): 
        bot.run(Config.TOKEN)
    else: 
        log.error("Config Error: Tokens or Guild IDs are missing in .env")
