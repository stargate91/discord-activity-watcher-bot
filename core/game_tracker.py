import discord
import datetime
import os
import re
from core.logger import log
from config_loader import Config

class GameTracker:
    def __init__(self, db):
        self.db = db
        self.franchises = {}

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
        log.info(f"Loaded {len(self.franchises)} tracked games.")

    async def handle_presence_update(self, before, after):
        """Automatically assigns roles based on the game franchise AND monitors all play activity."""
        if after.bot or not after.guild: return
        
        for activity in after.activities:
            if activity.type == discord.ActivityType.playing:
                game_to_log = activity.name
                bot_gave_role = False
                
                # Check if it's a tracked franchise for role assignment
                for franchise_key, role_suffix in self.franchises.items():
                    if franchise_key.lower() in activity.name.lower():
                        target_role_name = f"Player: {role_suffix}"
                        game_to_log = target_role_name # Use standardized name
                        role = discord.utils.get(after.guild.roles, name=target_role_name)
                        if role:
                            if role not in after.roles:
                                try: 
                                    await after.add_roles(role)
                                    log.info(f"Assigned {target_role_name} to {after.name}")
                                    self.db.log_role(after.id, after.guild.id, target_role_name)
                                    bot_gave_role = True
                                except discord.Forbidden: pass
                        break # Stop at first franchise match
                
                # Log the activity (standardized if it matched, raw if not)
                self.db.update_game_activity(after.id, after.guild.id, game_to_log, bot_assigned=bot_gave_role)

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
