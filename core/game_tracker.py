import discord
import datetime
import os
import re
from core.logger import log
from config_loader import Config

class GameTracker:
    def __init__(self, db, bot):
        self.db = db
        self.bot = bot
        self.franchises = {}
        self.active_sessions = {} # (main_id, guild_id, game_name): started_at
        self.playing_counts = {}  # (main_id, guild_id, game_name): number of accounts playing

    async def load_franchises(self):
        """Loads games from DB and includes hardcoded defaults if DB is empty."""
        db_games = self.db.get_tracked_games()
        
        if not db_games:
            # Fallback to defaults + save them to DB for first run
            defaults = {
                "Counter-Strike": "CS2", "The Sims": "Sims", "Apex Legends": "Apex Legends",
                "FINAL FANTASY": "Final Fantasy", "Age of Empires": "Age of Empires", 
                "Overwatch": "Overwatch", "Jurassic World Evolution": "Jurassic World Evolution",
                "Dota": "Dota 2", "League of Legends": "League of Legends", 
                "World of Warcraft": "World of Warcraft", "Space Engineers": "Space Engineers",
                "Fortnite": "Fortnite", "Stellaris": "Stellaris", "EVE Online": "EVE Online",
                "Valorant": "Valorant", "Minecraft": "Minecraft", "The Bazaar": "The Bazaar"
            }
            for sub, suf in defaults.items():
                self.db.add_tracked_game(sub, suf)
            self.franchises = defaults
        else:
            self.franchises = db_games
        
        # Load active sessions from DB
        db_sessions = self.db.get_active_game_sessions()
        self.active_sessions = db_sessions
        # Note: playing_counts will be populated as members are seen in on_ready or events
        log.info(f"Loaded {len(self.franchises)} tracked games and {len(self.active_sessions)} active game sessions.")

    def _get_games(self, member):
        games = set()
        for activity in member.activities:
            if activity.type == discord.ActivityType.playing and activity.name:
                name = activity.name
                # Standardize if matched
                for franchise_key, role_suffix in self.franchises.items():
                    if franchise_key.lower() in name.lower():
                        name = f"Player: {role_suffix}"
                        break
                games.add(name)
        return games

    async def handle_presence_update(self, before, after):
        if after.bot or not after.guild: return
        
        main_id = Config.get_main_id(after.id)
        before_games = self._get_games(before)
        after_games = self._get_games(after)
        
        # Started playing
        for game in (after_games - before_games):
            key = (main_id, after.guild.id, game)
            self.playing_counts[key] = self.playing_counts.get(key, 0) + 1
            
            if self.playing_counts[key] == 1:
                # First account started this game
                if key not in self.active_sessions:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    self.active_sessions[key] = now
                    self.db.start_game_session(main_id, after.guild.id, game, now)
                
                # Update role for ALL linked accounts
                bot_assigned = False
                if game.startswith("Player: "):
                    role = discord.utils.get(after.guild.roles, name=game)
                    if role:
                        bot_assigned = True
                        linked_members = [m for m in after.guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
                        for m in linked_members:
                            if role not in m.roles:
                                try:
                                    await m.add_roles(role)
                                    log.info(f"Assigned {game} to {m.name} (Alt Sync)")
                                except discord.Forbidden: pass

                self.db.update_game_activity(main_id, after.guild.id, game, bot_assigned=bot_assigned)

        # Stopped playing
        for game in (before_games - after_games):
            key = (main_id, after.guild.id, game)
            self.playing_counts[key] = max(0, self.playing_counts.get(key, 1) - 1)
            
            if self.playing_counts[key] == 0:
                # Last account stopped this game
                start_time = self.db.end_game_session(main_id, after.guild.id, game)
                if key in self.active_sessions:
                    start_time = self.active_sessions.pop(key)
                
                if start_time:
                    if start_time.tzinfo is None:
                        start_time = start_time.replace(tzinfo=datetime.timezone.utc)
                    duration = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() / 60
                    if duration > 0.1:
                        self.db.add_game_minutes(main_id, after.guild.id, game, duration)
                        log.info(f"Logged {duration:.2f}m of {game} for Main ID {main_id}")

    async def migrate_role_logs(self, bot):
        """Migrates existing role_log.txt into the database."""
        if not os.path.exists("role_log.txt"): return
        
        log.info("Migrating role_log.txt to database...")
        pattern = re.compile(r"\[(.*?)\] .*? \((\d+)\) -> (.*)")
        
        with open("role_log.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        count = 0
        for line in lines:
            match = pattern.search(line)
            if match:
                ts_str, uid, role = match.groups()
                for guild in bot.guilds:
                    if guild.get_member(int(uid)):
                        self.db.log_role(int(uid), guild.id, role, timestamp=ts_str)
                        count += 1
                        break
        
        if count > 0:
            os.rename("role_log.txt", "role_log_migrated.txt")
            log.info(f"Successfully migrated {count} logs to DB.")

    async def cleanup_inactive_roles(self, bot):
        """Eltávolítja a Player rangokat, ha X napja nem játszottak az adott játékkal."""
        for guild in bot.guilds:
            inactive = self.db.get_inactive_games(guild.id, days=Config.INACTIVE_GAME_DAYS)
            for uid, role_name in inactive:
                member = guild.get_member(uid)
                if not member: continue
                
                role = discord.utils.get(guild.roles, name=role_name)
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role)
                        log.info(f"Removed inactive role {role_name} from {member.name} ({Config.INACTIVE_GAME_DAYS} days inactivity)")
                        self.db.remove_game_activity(uid, guild.id, role_name)
                        self.db.log_role(uid, guild.id, role_name, action='REMOVED')
                    except discord.Forbidden: pass
