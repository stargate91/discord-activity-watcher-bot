import discord
from discord.ext import tasks, commands
import datetime
import random
from core.logger import log
from core.image_generator import get_welcome_card
from config_loader import Config
from core.messages import Messages
from core.activity_processor import ActivityProcessor
from core.ui_icons import Icons

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
        await self.bot.load_game_franchises()
        await self.bot.migrate_role_logs()
        
        # Initialize qualified voice states
        if not hasattr(self.bot, 'voice_qualified_states'):
            self.bot.voice_qualified_states = {}
        
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
                        
                        # Use AGGREGATE state of all linked accounts
                        linked_accounts = [m for m in guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
                        tier, is_streaming, stream_name = ActivityProcessor.get_best_tier(linked_accounts)
                        self.bot.voice_multipliers[main_id] = (tier, is_streaming, stream_name)
                    else:
                        # New session
                        now = datetime.datetime.now(datetime.timezone.utc)
                        linked_accounts = [m for m in guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
                        tier, is_streaming, stream_name = ActivityProcessor.get_best_tier(linked_accounts)
                        
                        if tier > 0:
                            self.bot.voice_start_times[main_id] = now
                            self.bot.voice_multipliers[main_id] = (tier, is_streaming, stream_name)
                            
                            # Initial qualify check
                            is_qual = ActivityProcessor.is_qualified(m)
                            self.bot.voice_qualified_states[main_id] = is_qual
                            
                            # Use any valid channel from linked accounts (or current member's)
                            chan_id = m.voice.channel.id
                            active_channel = next((acc.voice.channel for acc in linked_accounts if acc.voice and acc.voice.channel and acc.voice.channel.id != Config.AFK_CHANNEL_ID), m.voice.channel)
                            self.db.start_voice_session(main_id, guild.id, active_channel.id, now, tier, is_streaming, stream_name)
                
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
                            is_qual = self.bot.voice_qualified_states.pop(main_id, False)
                            
                            now = datetime.datetime.now(datetime.timezone.utc)
                            mins = (now - start).total_seconds() / 60
                            if mins > 0:
                                self.db.add_voice_minutes(main_id, guild.id, 0, mins, multiplier=mult, is_streaming=strm, is_qualified=is_qual)
                                log.info(f"Closed stale voice session for main user {main_id} ({int(mins)} mins credited at x{mult}, qualified={is_qual})")
                        self.bot.voice_multipliers.pop(main_id, None)

    @commands.Cog.listener()
    async def on_message(self, message):
        # This runs every time someone sends a message
        if message.author.bot or not message.guild: return
        if message.channel.id in Config.EXCLUDED_CHANNELS: return
        
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
        # if member.bot: return  # Ideiglenesen kikapcsolva a teszteléshez!
        log.info(f"Member joined: {member} (ID: {member.id})")
        main_id = Config.get_main_id(member.id)
        # Log event
        self.db.log_membership_event(main_id, member.guild.id, "JOIN", member.joined_at)
        # Update user record
        self.db.update_activity(main_id, member.guild.id)
        if member.joined_at:
            self.db.update_join_date(main_id, member.guild.id, member.joined_at)

        # Welcome Message
        if Config.WELCOME and Config.WELCOME.get("enabled", False):
            try:
                channel_id = Config.WELCOME.get("channel_id")
                if channel_id:
                    welcome_channel = member.guild.get_channel(channel_id)
                    if welcome_channel:
                        # 1. Format the greeting text
                        greeting_template = Config.WELCOME.get("greeting", "Hello {user.mention}, üdv a {guild.name} csatornáján!")
                        greeting = greeting_template.replace("{guild.name}", member.guild.name).replace("{user.name}", member.name).replace("{user.mention}", member.mention)

                        # 2. Get backgrounds
                        bg_urls = Config.WELCOME.get("images", [])
                        if not bg_urls and Config.WELCOME.get("image"):
                            bg_urls = [Config.WELCOME.get("image")]

                        # 3. Format Card Texts
                        main_text_template = Config.WELCOME.get("card_main_text", "{user.name} csatlakozott a szerverhez!")
                        main_text = main_text_template.replace("{guild.name}", member.guild.name).replace("{user.name}", member.name)
                        
                        member_count = len([m for m in member.guild.members if not m.bot])
                        sub_text_template = Config.WELCOME.get("card_sub_text", "Ő a {member_count}. tag")
                        sub_text = sub_text_template.replace("{member_count}", str(member_count))
                        
                        # 4. Generate the Image
                        avatar_url = member.display_avatar.url if member.display_avatar else None
                        
                        try:
                            image_buffer = await get_welcome_card(
                                avatar_url=avatar_url,
                                main_text=main_text,
                                sub_text=sub_text,
                                bg_urls=bg_urls,
                                style_config=Config.WELCOME
                            )
                            file = discord.File(fp=image_buffer, filename="welcome.png")
                            await welcome_channel.send(content=greeting, file=file)
                            
                        except Exception as e:
                            log.error(f"Image generation failed, falling back to text: {e}")
                            # Fallback ha esetleg mégis kell egy alap embed
                            embed = discord.Embed(color=0x3498DB)
                            if avatar_url: embed.set_thumbnail(url=avatar_url)
                            await welcome_channel.send(content=member.mention, embed=embed)
                            
            except Exception as e:
                log.error(f"Failed to send welcome message: {e}")

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
        
        # Aggregate all linked accounts to find the best tier (Streaming > Video > Voice)
        linked_accounts = [m for m in member.guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
        new_tier, is_streaming, stream_name = ActivityProcessor.get_best_tier(linked_accounts)
        
        old_data = self.bot.voice_multipliers.get(main_id, (0.0, False, "Inactive"))
        old_tier, old_streaming, old_name = old_data
        old_qual = self.bot.voice_qualified_states.get(main_id, False)
        is_tracking = main_id in self.bot.voice_start_times
        
        # New qualification check
        new_qual = ActivityProcessor.is_qualified(member)
        
        # Detect State Change (Best tier, stream name, OR qualification state changed)
        state_changed = (new_tier != old_tier) or (stream_name != old_name) or (new_qual != old_qual)
        # Note: channel_changed is still relevant if the *specific account* that triggered the event changed channels
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
                        mins, multiplier=old_tier, is_streaming=old_streaming, is_qualified=old_qual
                    )
                    if before.channel:
                        self.db.log_voice_session(main_id, member.guild.id, before.channel.id, start, now, mins, stream_detail=old_name)
                    
                    # Check for role assignment after crediting qualified minutes
                    if old_qual:
                        await self.check_basic_member_award(member)
            
            # Clean up if they are no longer tracking
            if new_tier == 0:
                self.bot.voice_start_times.pop(main_id, None)
                self.bot.voice_multipliers.pop(main_id, None)
                self.bot.voice_qualified_states.pop(main_id, None)
            else:
                # Start new segment with new tier
                self.bot.voice_start_times[main_id] = now
                self.bot.voice_multipliers[main_id] = (new_tier, is_streaming, stream_name)
                self.bot.voice_qualified_states[main_id] = new_qual
                # Pick a representative channel from any active linked account
                active_channel = next((acc.voice.channel for acc in linked_accounts if acc.voice and acc.voice.channel and acc.voice.channel.id != Config.AFK_CHANNEL_ID), after.channel)
                chan_id = active_channel.id if active_channel else 0
                
                # Record to DB with new multiplier/streaming state
                self.db.start_voice_session(main_id, member.guild.id, chan_id, now, new_tier, is_streaming, stream_name)

        # Step 2: Handle NEW sessions (was not tracking, now active)
        elif not is_tracking and new_tier > 0:
            active_channel = next((acc.voice.channel for acc in linked_accounts if acc.voice and acc.voice.channel and acc.voice.channel.id != Config.AFK_CHANNEL_ID), after.channel)
            self.db.start_voice_session(main_id, member.guild.id, active_channel.id, now, new_tier, is_streaming, stream_name)
            self.bot.voice_start_times[main_id] = now
            self.bot.voice_multipliers[main_id] = (new_tier, is_streaming, stream_name)
            self.bot.voice_qualified_states[main_id] = new_qual
            await self.handle_member_activity(member)
        
        # Step 3: Handle "Alone" status changes for OTHERS in the channel
        # If someone joined or left, the 'is_alone' status of others might have changed.
        # We manually trigger a segment refresh for them if they are tracking.
        affected_channels = []
        if before.channel: affected_channels.append(before.channel)
        if after.channel and after.channel != before.channel: affected_channels.append(after.channel)

        for channel in affected_channels:
            for m in channel.members:
                if m.id == member.id or m.bot: continue
                m_main_id = Config.get_main_id(m.id)
                if m_main_id in self.bot.voice_start_times:
                    # Check if their qualification state changed just because of this move
                    m_new_qual = ActivityProcessor.is_qualified(m)
                    m_old_qual = self.bot.voice_qualified_states.get(m_main_id, False)
                    if m_new_qual != m_old_qual:
                        # Qualification changed! Refresh their session
                        # We don't want to recurse infinitely, so we just do a direct update
                        m_now = datetime.datetime.now(datetime.timezone.utc)
                        m_sess_data = self.db.end_voice_session(m_main_id, m.guild.id)
                        if m_sess_data:
                            m_start = m_sess_data["joined_at"]
                            m_mins = (m_now - m_start).total_seconds() / 60
                            if m_mins > 0:
                                m_old_data = self.bot.voice_multipliers.get(m_main_id, (0.0, False, "Inactive"))
                                self.db.add_voice_minutes(
                                    m_main_id, m.guild.id, channel.id, m_mins, 
                                    multiplier=m_old_data[0], is_streaming=m_old_data[1], is_qualified=m_old_qual
                                )
                                self.db.log_voice_session(m_main_id, m.guild.id, channel.id, m_start, m_now, m_mins, stream_detail=m_old_data[2])
                                if m_old_qual:
                                    await self.check_basic_member_award(m)

                        # Start new segment for them
                        self.bot.voice_start_times[m_main_id] = m_now
                        self.bot.voice_qualified_states[m_main_id] = m_new_qual
                        self.db.start_voice_session(m_main_id, m.guild.id, channel.id, m_now, m_old_data[0], m_old_data[1], m_old_data[2])
    
    async def check_basic_member_award(self, member):
        """Checks if a user qualifies for the Basic Member role and awards it to all linked accounts."""
        if Config.BASIC_MEMBER_ROLE_ID == 0: return
        
        main_id = Config.get_main_id(member.id)
        current_data = self.db.get_user_data(main_id, member.guild.id)
        if not current_data: return
        
        qual_mins = current_data.get("qualified_voice_minutes", 0)
        if qual_mins >= Config.BASIC_MEMBER_THRESHOLD_MINS:
            role = member.guild.get_role(Config.BASIC_MEMBER_ROLE_ID)
            if not role: return
            
            # Find all linked accounts in this guild
            all_linked = [m for m in member.guild.members if Config.get_main_id(m.id) == main_id and not m.bot]
            
            for m in all_linked:
                if role not in m.roles:
                    # Check exclusions again (just in case they got an exclusion role recently)
                    if any(er_id in [r.id for r in m.roles] for er_id in Config.BASIC_MEMBER_EXCLUDED_ROLES):
                        continue
                        
                    try:
                        await m.add_roles(role)
                        log.info(f"Awarded Basic Member role to {m.display_name} ({m.id}) - Qualified: {int(qual_mins)} mins")
                        self.db.log_role(main_id, member.guild.id, role.name, action="ADDED")
                    except discord.Forbidden:
                        log.warning(f"Forbidden: Could not add Basic Member role to {m.display_name}. Hierarchy issue?")
                    except Exception as e:
                        log.error(f"Error awarding Basic Member role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # This runs when someone adds a reaction (emoji) to a message
        if payload.guild_id:
            if payload.channel_id in Config.EXCLUDED_CHANNELS: return
            
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
