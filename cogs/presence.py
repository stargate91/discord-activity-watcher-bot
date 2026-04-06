import discord
from discord.ext import tasks, commands
import random
import datetime
from core.logger import log
from config_loader import Config
from core.messages import Messages
from core.ui_icons import Icons

class PresenceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.current_index = 0
        self.categories = Config.PRESENCE_ROTATION
        
    def cog_load(self):
        if not self.presence_task.is_running():
            self.presence_task.change_interval(minutes=Config.PRESENCE_ROTATION_MINUTES)
            self.presence_task.start()

    def cog_unload(self):
        self.presence_task.cancel()

    @tasks.loop(minutes=5)
    async def presence_task(self):
        if not self.bot.is_ready(): return
        
        try:
            if not self.categories:
                # Fallback if no categories are defined
                activity = discord.Activity(type=discord.ActivityType.watching, name=Messages.PRESENCE_WATCHING)
                await self.bot.change_presence(activity=activity)
                return

            category = self.categories[self.current_index % len(self.categories)]
            self.current_index += 1
            
            activity = None
            
            if category == "stats":
                # Pick a random stat
                stat_type = random.choice(["players", "voice", "games"])
                if stat_type == "players":
                    # Count unique main_ids in active game sessions (excluding Spotify)
                    playing = set()
                    for (mid, gid, game) in self.bot.tracker.active_sessions.keys():
                        if game != "Spotify": playing.add(mid)
                    count = len(playing)
                    activity = discord.Activity(
                        type=discord.ActivityType.watching, 
                        name=Messages.PRESENCE_WATCHING_PLAYERS.replace("{count}", str(count))
                    )
                elif stat_type == "voice":
                    count = len(self.bot.voice_start_times)
                    activity = discord.Activity(
                        type=discord.ActivityType.listening, 
                        name=Messages.PRESENCE_LISTENING_VOICE.replace("{count}", str(count))
                    )
                else: # games
                    active_games = set()
                    for (mid, gid, game) in self.bot.tracker.active_sessions.keys():
                        if game != "Spotify": active_games.add(game)
                    count = len(active_games)
                    activity = discord.Activity(
                        type=discord.ActivityType.playing, 
                        name=Messages.PRESENCE_TRACKING_GAMES.replace("{count}", str(count))
                    )

            elif category == "champions":
                # Get the most recent champions across all guilds (keep it simple)
                champs = {}
                for guild in self.bot.guilds:
                    guild_champs = self.db.get_last_champions(guild.id)
                    champs.update(guild_champs)
                
                if champs:
                    cat, uid = random.choice(list(champs.items()))
                    user = self.bot.get_user(uid)
                    name = user.display_name if user else f"User {uid}"
                    # Translate category if needed (CAT_SPOTIFY etc.)
                    cat_map = {
                        "spotify": Messages.CAT_SPOTIFY,
                        "gamer_total": Messages.CAT_GAMER_TOTAL,
                        "gamer_variety": Messages.CAT_GAMER_VARIETY,
                        "streamer": Messages.CAT_STREAMER,
                        "media": Messages.CAT_MEME
                    }
                    cat_name = cat_map.get(cat, cat)
                    activity = discord.Activity(
                        type=discord.ActivityType.watching,
                        name=Messages.PRESENCE_PRAISING_CHAMPION.replace("{user}", name).replace("{category}", cat_name)
                    )
                else:
                    category = "sassy" # Fallback

            elif category == "games":
                # Get top game from the first guild (usually enough for status)
                if self.bot.guilds:
                    stats = self.db.get_game_stats_report(self.bot.guilds[0].id, timeframe="monthly")
                    if stats:
                        top_game = stats[0][0] # Clean name
                        activity = discord.Activity(
                            type=discord.ActivityType.playing,
                            name=Messages.PRESENCE_TOP_GAME.replace("{game}", top_game)
                        )
                
                if not activity:
                    category = "sassy" # Fallback

            if category == "sassy":
                sassy_msgs = [
                    Messages.PRESENCE_WATCHING,
                    Messages.PRESENCE_SASSY_1,
                    Messages.PRESENCE_SASSY_2,
                    Messages.PRESENCE_SASSY_3,
                    Messages.PRESENCE_SASSY_4
                ]
                msg = random.choice(sassy_msgs)
                activity = discord.Activity(type=discord.ActivityType.watching, name=msg)

            elif category == "help":
                activity = discord.Activity(type=discord.ActivityType.playing, name=Messages.PRESENCE_HELP)

            if activity:
                # Truncate to 35 chars for clean display if needed
                if len(activity.name) > 35:
                    activity.name = activity.name[:32] + "..."
                    
                await self.bot.change_presence(activity=activity)
                log.debug(f"Presence updated to: {activity.name}")

        except Exception as e:
            log.error(f"Error updating presence rotation: {e}")

    @presence_task.before_loop
    async def before_presence_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PresenceCog(bot))
