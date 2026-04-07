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
        self.active_sessions = {} # This keeps track of who started playing what and when!
        self.playing_counts = {}  # This counts how many of your accounts (main + alts) are playing the same game

    async def load_franchises(self):
        # This function loads the list of games we care about from the database.
        # If we haven't added any games yet, it uses the default ones we set in the config.
        db_games = self.db.get_tracked_games()
        
        if not db_games:
            # Fallback to defaults from config + save them to DB for first run
            defaults = Config.DEFAULT_GAMES
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
        """This helper function finds all the games someone is currently playing on their Discord status!"""
        games = set()
        for activity in member.activities:
            if activity.type == discord.ActivityType.playing and activity.name:
                name = activity.name
                # Standardize if matched
                for franchise_key, role_suffix in self.franchises.items():
                    if franchise_key.lower() in name.lower():
                        name = f"{Config.GAME_ROLE_PREFIX}{role_suffix}"
                        break
                games.add(name)
        return games

    async def handle_presence_update(self, before, after):
        # This part runs every time someone starts or stops playing a game, or changes their status!
        if after.bot or not after.guild: return
        
        main_id = Config.get_main_id(after.id)
        
        # Let's see what games they were playing before and what they are playing now.
        before_games = self._get_games(before)
        after_games = self._get_games(after)
        
        # Now let's check if they are listening to some music on Spotify!
        before_spotify = any(a.type == discord.ActivityType.listening and a.name == "Spotify" for a in before.activities)
        after_spotify = any(a.type == discord.ActivityType.listening and a.name == "Spotify" for a in after.activities)
        
        # Spotify Started
        if after_spotify and not before_spotify:
            key = (main_id, after.guild.id, "Spotify")
            if key not in self.active_sessions:
                now = datetime.datetime.now(datetime.timezone.utc)
                self.active_sessions[key] = now
                self.db.start_game_session(main_id, after.guild.id, "Spotify", now)
        
        # Spotify Stopped
        if before_spotify and not after_spotify:
            key = (main_id, after.guild.id, "Spotify")
            start_time = self.db.end_game_session(main_id, after.guild.id, "Spotify")
            if key in self.active_sessions:
                start_time = self.active_sessions.pop(key)
            
            if start_time:
                if start_time.tzinfo is None:
                    start_time = start_time.replace(tzinfo=datetime.timezone.utc)
                duration = (datetime.datetime.now(datetime.timezone.utc) - start_time).total_seconds() / 60
                if duration > 0.1:
                    self.db.add_spotify_minutes(main_id, after.guild.id, duration)
                    log.info(f"Logged {duration:.2f}m of Spotify for Main ID {main_id}")

        # Now we handle the logic for starting a new game!
        # If they just opened a game, we start a stopwatch for them.
        for game in (after_games - before_games):
            key = (main_id, after.guild.id, game)
            self.playing_counts[key] = self.playing_counts.get(key, 0) + 1
            
            if self.playing_counts[key] == 1:
                # First account started this game - now the timer starts!
                if key not in self.active_sessions:
                    now = datetime.datetime.now(datetime.timezone.utc)
                    self.active_sessions[key] = now
                    self.db.start_game_session(main_id, after.guild.id, game, now)
                
                # If it's a game we track, give them the special role
                bot_assigned = False
                if game.startswith(Config.GAME_ROLE_PREFIX):
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

        # And here we handle what happens when they stop playing!
        # When they close a game, we stop the stopwatch and save their time.
        for game in (before_games - after_games):
            key = (main_id, after.guild.id, game)
            self.playing_counts[key] = max(0, self.playing_counts.get(key, 1) - 1)
            
            if self.playing_counts[key] == 0:
                # They are not playing this game on any of their accounts anymore
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



    async def cleanup_inactive_roles(self, bot):
        # This function cleans up old 'Player' roles from people who haven't played a game in a long time!
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
