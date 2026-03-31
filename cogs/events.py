import discord
from discord.ext import tasks, commands
import datetime
from core.logger import log
from config_loader import Config
from core.messages import Messages
from core.activity_processor import ActivityProcessor

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.tracker = bot.tracker
        
    def cog_load(self):
        if not self.check_inactivity_task.is_running():
            self.check_inactivity_task.start()
        if not self.cleanup_inactive_roles_task.is_running():
            self.cleanup_inactive_roles_task.start()

    def cog_unload(self):
        self.check_inactivity_task.cancel()
        self.cleanup_inactive_roles_task.cancel()

    # Logic moved to ActivityProcessor

    async def handle_member_activity(self, member: discord.Member, event_type=None, channel_id=None):
        # This part updates the database whenever someone sends a message or adds a reaction
        if member.bot: return
        if channel_id and channel_id in Config.EXCLUDED_CHANNELS: return
            
        main_id = Config.get_main_id(member.id)
        self.db.update_activity(main_id, member.guild.id)
        
        # Ensure joined_at is set if missing (lazy sync)
        if not self.db.get_user_join_date(main_id, member.guild.id):
            if hasattr(member, 'joined_at') and member.joined_at:
                self.db.update_join_date(main_id, member.guild.id, member.joined_at)
        if event_type == "message":
            # Dynamic Scoring: Points = Base + min(Length / Scale, Max)
            # member here is used to get the content if available (but handle_member_activity doesn't have message)
            # I should move the point calculation to on_message or pass points as argument.
            pass 
        elif event_type == "reaction":
            self.db.increment_reactions(main_id, member.guild.id, channel_id, points=Config.POINTS_REACTION)
        
        # Find all linked accounts in this guild to sync roles
        all_linked = [m for m in member.guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
        
        stage1_role = member.guild.get_role(Config.STAGE_1_ROLE_ID)
        stage2_role = member.guild.get_role(Config.STAGE_2_ROLE_ID)
        
        # Determine current stats from DB
        data = self.db.get_user_data(main_id, member.guild.id)
        
        # This part handles the 'Inactive' (Stage 1) and 'Returned' (Stage 2) roles
        for m in all_linked:
            if stage1_role and stage1_role in m.roles:
                try:
                    stats = self.db.get_user_data(main_id, member.guild.id)
                    if stage2_role and stage2_role not in m.roles:
                        await m.add_roles(stage2_role)
                    await m.remove_roles(stage1_role)
                    self.db.set_returned_at(main_id, member.guild.id, datetime.datetime.now(datetime.timezone.utc))
                except discord.Forbidden:
                    log.warning(f"Forbidden: Could not toggle Stage 1/2 roles for {m.display_name} in {member.guild.name}. Check bot role hierarchy.")
            elif stage2_role and stage2_role in m.roles:
                if data and data["returned_at"]:
                    delta = datetime.datetime.now(datetime.timezone.utc) - data["returned_at"].astimezone(datetime.timezone.utc)
                    if 60 <= delta.total_seconds() <= (Config.STAGE_2_GRACE_DAYS * 24 * 3600):
                        try: 
                            await m.remove_roles(stage2_role)
                            self.db.set_returned_at(main_id, member.guild.id, None)
                        except discord.Forbidden:
                            log.warning(f"Forbidden: Could not remove Stage 2 role from {m.display_name} in {member.guild.name}. Check bot role hierarchy.")

    @commands.Cog.listener()
    async def on_ready(self):
        # This runs when the bot starts up and is ready to work
        await self.bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=Messages.PRESENCE_WATCHING))
        await self.bot.load_game_franchises()
        await self.bot.migrate_role_logs()
        
        log.info(f"Cog Events: Bot ready as {self.bot.user}")
        
        # 1. Load active voice sessions from the database
        db_sessions = self.db.get_active_voice_sessions()
        
        # 2. Sync with current voice channels across all servers (guilds)
        # We do this so if someone joined while the bot was offline, we don't miss them!
        for guild in self.bot.guilds:
            # Sync user data existence
            for m in guild.members:
                if m.bot: continue
                if not self.db.get_user_data(Config.get_main_id(m.id), guild.id):
                    self.db.update_activity(Config.get_main_id(m.id), guild.id)
                
                # Automated Join Date Sync
                main_id = Config.get_main_id(m.id)
                if not self.db.get_user_join_date(main_id, guild.id):
                    if m.joined_at:
                        self.db.update_join_date(main_id, guild.id, m.joined_at)
                        log.debug(f"Synced join date for {m.display_name}: {m.joined_at}")
            
            # Sync voice sessions
            for m in guild.members:
                if m.bot: continue
                is_in_voice = m.voice and m.voice.channel and m.voice.channel.id != Config.AFK_CHANNEL_ID and m.voice.channel != guild.afk_channel
                main_id = Config.get_main_id(m.id)
                
                # Case A: In voice now
                if is_in_voice:
                    if main_id in self.bot.voice_start_times:
                        # Already tracking this user (or another linked account)
                        continue
                        
                    if main_id in db_sessions:
                        # Continue existing session from DB
                        sess = db_sessions[main_id]
                        self.bot.voice_start_times[main_id] = sess["joined_at"]
                        self.bot.voice_multipliers[main_id] = (sess["multiplier"], sess["is_streaming"], sess["stream_name"])
                    else:
                        # New session
                        now = datetime.datetime.now(datetime.timezone.utc)
                        tier, is_streaming, stream_name = ActivityProcessor.get_participation_tier(main_id, guild)
                        
                        if tier > 0:
                            self.bot.voice_start_times[main_id] = now
                            self.bot.voice_multipliers[main_id] = (tier, is_streaming, stream_name)
                            # Now with full metadata
                            self.db.start_voice_session(main_id, guild.id, m.voice.channel.id, now, tier, is_streaming, stream_name)
                
                # Case B: In DB session but NOT in voice now
                elif main_id in db_sessions:
                    # Only close if NO linked accounts are in voice anywhere in this guild
                    is_someone_still_in = any(
                        Config.get_main_id(other.id) == main_id and 
                        other.voice and other.voice.channel and 
                        other.voice.channel.id != Config.AFK_CHANNEL_ID
                        for other in guild.members if not other.bot
                    )
                    
                    if not is_someone_still_in:
                        sess_data = self.db.end_voice_session(main_id, guild.id)
                        self.bot.voice_start_times.pop(main_id, None)
                        if sess_data:
                            start = sess_data["joined_at"]
                            mult = sess_data["multiplier"]
                            strm = sess_data["is_streaming"]
                            
                            now = datetime.datetime.now(datetime.timezone.utc)
                            mins = (now - start).total_seconds() / 60
                            if mins > 0:
                                self.db.add_voice_minutes(main_id, guild.id, 0, mins, multiplier=mult, is_streaming=strm)
                                log.info(f"Closed stale voice session for main user {main_id} ({int(mins)} mins credited at x{mult})")
                        self.bot.voice_multipliers.pop(main_id, None)

    @commands.Cog.listener()
    async def on_message(self, message):
        # This runs every time someone sends a message
        if message.author.bot or not message.guild: return
        
        try:
            # Calculate dynamic points: Base (1) + min(Length / 10, 100)
            points = ActivityProcessor.calculate_message_points(message.content)
            
            # 1. Media Detection (Attachments or specific Links)
            has_media = ActivityProcessor.is_media(message)
            
            # We still call handle_member_activity for side effects (roles, activity times)
            await self.handle_member_activity(message.author, event_type=None, channel_id=message.channel.id)
            
            # Manually call increment_messages with calculated points
            main_id = Config.get_main_id(message.author.id)
            self.db.increment_messages(main_id, message.guild.id, message.channel.id, points=points)
            
            # 2. Increment Media if found (+ bonus points)
            if has_media:
                self.db.increment_media(main_id, message.guild.id, message.channel.id, points=Config.POINTS_MEDIA_BONUS)
                
        except Exception as e:
            log.error(f"Error in on_message handler: {e}")
            # Optional: Report error to admin channel? 
            # (Keep it simple for now, logging is enough)

    @commands.Cog.listener()
    async def on_presence_update(self, before, after):
        await self.tracker.handle_presence_update(before, after)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot: return
        log.info(f"Member joined: {member} (ID: {member.id})")
        main_id = Config.get_main_id(member.id)
        # Log event
        self.db.log_membership_event(main_id, member.guild.id, "JOIN", member.joined_at)
        # Update user record
        self.db.update_activity(main_id, member.guild.id)
        if member.joined_at:
            self.db.update_join_date(main_id, member.guild.id, member.joined_at)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.bot: return
        log.info(f"Member left: {member} (ID: {member.id})")
        main_id = Config.get_main_id(member.id)
        # Log event
        self.db.log_membership_event(main_id, member.guild.id, "LEAVE")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # This runs when someone joins, leaves, or moves between voice channels
        if member.bot: return
        
        main_id = Config.get_main_id(member.id)
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # Determine current and previous states
        new_tier, is_streaming, stream_name = ActivityProcessor.get_participation_tier(main_id, member.guild)
        old_data = self.bot.voice_multipliers.get(main_id, (0.0, False, None))
        old_tier, old_streaming, old_name = old_data
        is_tracking = main_id in self.bot.voice_start_times
        
        # Step 1: Detect State Change (Channel move, Mute/Deaf toggle, or Stream toggle/app change)
        state_changed = (new_tier != old_tier) or (stream_name != old_name)
        channel_changed = (before.channel != after.channel)
        
        if is_tracking and (state_changed or channel_changed):
            # Close previous segment
            sess_data = self.db.end_voice_session(main_id, member.guild.id)
            if sess_data:
                start = sess_data["joined_at"]
                mins = (now - start).total_seconds() / 60
                if mins > 0:
                    # Use the tier and streaming state they WERE at for this segment
                    self.db.add_voice_minutes(
                        main_id, member.guild.id, 
                        (before.channel.id if before.channel else 0), 
                        mins, multiplier=old_tier, is_streaming=old_streaming
                    )
                    if before.channel:
                        self.db.log_voice_session(main_id, member.guild.id, before.channel.id, start, now, mins, stream_detail=old_name)
            
            # Clean up if they are no longer tracking
            if new_tier == 0:
                self.bot.voice_start_times.pop(main_id, None)
                self.bot.voice_multipliers.pop(main_id, None)
            else:
                # Start new segment with new tier
                self.bot.voice_start_times[main_id] = now
                self.bot.voice_multipliers[main_id] = (new_tier, is_streaming, stream_name)
                chan_id = after.channel.id if after.channel else 0
                # Record to DB with new multiplier/streaming state
                self.db.start_voice_session(main_id, member.guild.id, chan_id, now, new_tier, is_streaming, stream_name)

        # Step 2: Handle NEW sessions (was not tracking, now active)
        elif not is_tracking and new_tier > 0:
            self.db.start_voice_session(main_id, member.guild.id, after.channel.id, now, new_tier, is_streaming, stream_name)
            self.bot.voice_start_times[main_id] = now
            self.bot.voice_multipliers[main_id] = (new_tier, is_streaming, stream_name)
            await self.handle_member_activity(member)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # This runs when someone adds a reaction (emoji) to a message
        if payload.guild_id:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild: return
            member = payload.member or await guild.fetch_member(payload.user_id)
            if member: 
                main_id = Config.get_main_id(member.id)
                await self.handle_member_activity(member, event_type="reaction", channel_id=payload.channel_id)
                try:
                    channel = self.bot.get_channel(payload.channel_id)
                    if channel:
                        message = discord.utils.get(self.bot.cached_messages, id=payload.message_id)
                        if not message:
                            message = await channel.fetch_message(payload.message_id)
                        
                        if message and message.author and not message.author.bot:
                            target_main_id = Config.get_main_id(message.author.id)
                            if target_main_id != main_id:
                                self.db.log_reaction_interaction(
                                    user_id=main_id,
                                    target_user_id=target_main_id,
                                    guild_id=guild.id,
                                    channel_id=channel.id,
                                    message_id=payload.message_id,
                                    emoji=str(payload.emoji)
                                )
                except discord.NotFound:
                    pass # Message/channel might have been deleted quickly
                except discord.Forbidden:
                    log.warning(f"Forbidden: Could not fetch message {payload.message_id} in {guild.name}. Check channel permissions.")
                except Exception as e:
                    log.debug(f"Error in reaction logging: {e}")

    @tasks.loop(hours=Config.CHECK_INTERVAL_HOURS) 
    async def check_inactivity_task(self):
        # This background task runs every few hours to check who is 'lazy' (inactive)
        now = datetime.datetime.now(datetime.timezone.utc)
        for guild in self.bot.guilds:
            r1, r2 = guild.get_role(Config.STAGE_1_ROLE_ID), guild.get_role(Config.STAGE_2_ROLE_ID)
            if not r1: continue
            data = self.db.get_inactive_users(guild.id, Config.STAGE_1_DAYS)
            for uid, d in data.items():
                # Skip if this is an alt ID (to avoid processing same 'person' multiple times)
                if Config.get_main_id(uid) != uid: continue
                
                # Find all entities for this "person" in the guild
                members = [m for m in guild.members if Config.get_main_id(m.id) == uid and not m.bot]
                if not members: continue
                
                inactive_days = (now - d["last_active"].astimezone(datetime.timezone.utc)).days
                for m in members:
                    if inactive_days >= Config.STAGE_1_DAYS:
                        if r1 not in m.roles:
                            try:
                                await m.add_roles(r1)
                                if r2 and r2 in m.roles: await m.remove_roles(r2)
                                self.db.set_returned_at(uid, guild.id, None)
                            except discord.Forbidden:
                                log.warning(f"Forbidden: Could not manage inactivity roles for {m.display_name} in {guild.name}. Check bot role hierarchy.")
                    elif d["returned_at"]:
                        if (now - d["returned_at"].astimezone(datetime.timezone.utc)).days >= Config.STAGE_2_GRACE_DAYS:
                            if r2 and r2 in m.roles:
                                try: await m.remove_roles(r2)
                                except discord.Forbidden:
                                    log.warning(f"Forbidden: Could not remove grace role for {m.display_name} in {guild.name}. Check bot role hierarchy.")
                            self.db.set_returned_at(uid, guild.id, None)

    @tasks.loop(hours=24)
    async def cleanup_inactive_roles_task(self):
        await self.tracker.cleanup_inactive_roles(self.bot)

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
