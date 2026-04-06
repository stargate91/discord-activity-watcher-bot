import discord
from discord.ext import commands
import datetime
import asyncio
from config_loader import Config
from core.logger import log
from core.messages import Messages
from core.message_db import MessageArchiveDB
from discord.ext import tasks

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.archive_db = MessageArchiveDB()
        self.prune_archive_loop.start()
        self.historical_sync_loop.start()

    def cog_unload(self):
        self.prune_archive_loop.cancel()
        self.historical_sync_loop.cancel()

    @tasks.loop(hours=24)
    async def prune_archive_loop(self):
        if not Config.LOGGING.get("archive", {}).get("enabled", False):
            return
            
        retention = Config.LOGGING.get("archive", {}).get("retention_days", 30)
        max_size = Config.LOGGING.get("archive", {}).get("max_size_mb", 1000)
        r = retention if retention > 0 else None
        m = max_size if max_size > 0 else None
        count = self.archive_db.prune_database(r, m)
        if count > 0:
            log.info(f"Message archive pruned {count} old messages.")

    @prune_archive_loop.before_loop
    async def before_prune(self):
        await self.bot.wait_until_ready()

    @tasks.loop(seconds=1.0)
    async def historical_sync_loop(self):
        sync_cfg = Config.LOGGING.get("archive", {}).get("historical_sync", {})
        if not sync_cfg.get("enabled", False) or not Config.LOGGING.get("archive", {}).get("enabled", False):
            await asyncio.sleep(60)
            return

        delay = sync_cfg.get("delay_seconds", 10)
        batch = sync_cfg.get("batch_size", 100)
        batch = min(100, batch) if batch > 0 else None

        channel_to_sync = None
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                permissions = channel.permissions_for(guild.me)
                if not permissions.read_message_history or not permissions.read_messages:
                    continue

                state = self.archive_db.get_sync_state(channel.id)
                if not state["is_completed"]:
                    channel_to_sync = channel
                    break
            if channel_to_sync:
                break
                
        if not channel_to_sync:
            await asyncio.sleep(60)
            return

        state = self.archive_db.get_sync_state(channel_to_sync.id)
        before_obj = discord.Object(id=state["oldest_message_id"]) if state["oldest_message_id"] else None
        
        try:
            messages = [m async for m in channel_to_sync.history(limit=batch, before=before_obj)]
            if not messages:
                self.archive_db.update_sync_state(channel_to_sync.id, state["oldest_message_id"], True)
                log.info(f"Historical archive sync COMPLETED for #{channel_to_sync.name}")
            else:
                for message in messages:
                    attachments = "\n".join([a.url for a in message.attachments]) if message.attachments else ""
                    self.archive_db.insert_message(
                        message.id,
                        message.guild.id,
                        message.channel.id,
                        message.author.id,
                        message.author.name,
                        message.author.bot,
                        message.content,
                        attachments,
                        message.created_at
                    )
                # Messages are fetched newest to oldest
                oldest_id = messages[-1].id
                self.archive_db.update_sync_state(channel_to_sync.id, oldest_id, False)
                log.info(f"Historical archive sync: Saved {len(messages)} messages from #{channel_to_sync.name}...")
        except discord.Forbidden:
            self.archive_db.update_sync_state(channel_to_sync.id, state["oldest_message_id"], True)
        except Exception as e:
            log.error(f"Error during historical sync for {channel_to_sync.name}: {e}")

        await asyncio.sleep(delay)

    @historical_sync_loop.before_loop
    async def before_historical_sync(self):
        await self.bot.wait_until_ready()

    def get_log_channel(self, event_name):
        """Helper to get the appropriate channel for an event."""
        if not Config.LOGGING.get("enabled", False):
            return None
        
        event_cfg = Config.LOGGING.get("events", {}).get(event_name, {})
        if not event_cfg.get("enabled", False):
            return None
        
        channel_id = event_cfg.get("channel_id") or Config.LOGGING.get("global_channel_id")
        if not channel_id:
            return None
            
        return self.bot.get_channel(int(channel_id))

    def create_base_embed(self, member, title, color):
        """Creates a consistent premium embed style."""
        embed = discord.Embed(
            description=title,
            color=int(color, 16) if isinstance(color, str) else color,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_author(name=f"@{member.name}", icon_url=member.display_avatar.url)
        return embed

    def add_footer_info(self, embed, user_id):
        """Adds User ID to the footer."""
        embed.set_footer(text=f"User ID: {user_id}")

    def should_log_user(self, user, is_guild=True):
        if not is_guild: 
            return False
        if user.bot:
            if user == self.bot.user:
                return Config.LOGGING.get("log_self", True)
            else:
                return Config.LOGGING.get("log_bots", False)
        return True

    async def get_audit_log_user(self, guild, action_type, target_id=None):
        """Fetches the user responsible for an action from the audit log."""
        if not guild.me.guild_permissions.view_audit_log:
            return None
        try:
            async for entry in guild.audit_logs(action=action_type, limit=5):
                if target_id is None or entry.target.id == target_id:
                    return entry.user
        except discord.Forbidden:
            pass
        return None

    @commands.Cog.listener()
    async def on_message(self, message):
        if not Config.LOGGING.get("archive", {}).get("enabled", False): return
        if not message.guild: return
        attachments = "\n".join([a.url for a in message.attachments]) if message.attachments else ""
        self.archive_db.insert_message(
            message.id,
            message.guild.id,
            message.channel.id,
            message.author.id,
            message.author.name,
            message.author.bot,
            message.content,
            attachments,
            message.created_at
        )

    # Message Events
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        channel = self.get_log_channel("message_delete")
        if not channel: return

        if payload.channel_id == channel.id:
            return

        message = payload.cached_message
        channel_obj = self.bot.get_channel(payload.channel_id)
        channel_mention = channel_obj.mention if channel_obj else f"<#{payload.channel_id}>"

        if message:
            if not self.should_log_user(message.author, message.guild):
                return
            title = Messages.LOG_MSG_DELETE.format(channel=channel_mention)
            embed = self.create_base_embed(message.author, title, Config.COLOR_DANGER)
            if message.content:
                embed.add_field(name="Content", value=message.content[:1024], inline=False)
            self.add_footer_info(embed, message.author.id)
        else:
            # Uncached message
            title = Messages.LOG_MSG_DELETE.format(channel=channel_mention)
            embed = discord.Embed(
                description=title,
                color=Config.COLOR_DANGER,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text=f"Message ID: {payload.message_id}")

            archive_msg = None
            if Config.LOGGING.get("archive", {}).get("enabled", False):
                archive_msg = self.archive_db.get_message(payload.message_id)
                
            if archive_msg:
                if archive_msg['is_bot']:
                    if str(archive_msg['user_id']) == str(self.bot.user.id):
                        if not Config.LOGGING.get("log_self", True): return
                    else:
                        if not Config.LOGGING.get("log_bots", False): return

                embed.set_author(name=f"@{archive_msg['username']}")
                embed.add_field(name="Content (Archived)", value=archive_msg['content'][:1024] or "*Empty*", inline=False)
                if archive_msg['attachments']:
                    embed.add_field(name="Attachments", value=archive_msg['attachments'][:1024], inline=False)
                self.add_footer_info(embed, archive_msg['user_id'])
            else:
                embed.add_field(name="Content", value="*Message content unknown (not cached & not in archive)*", inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel = self.get_log_channel("message_edit")
        if not channel: return

        if payload.channel_id == channel.id:
            return

        # Raw payload might not have 'content' if it wasn't modified or if it's not cached
        before_msg = payload.cached_message
        
        # 'payload.data' contains the new state of the message
        after_content = payload.data.get("content")
        channel_obj = self.bot.get_channel(payload.channel_id)
        channel_mention = channel_obj.mention if channel_obj else f"<#{payload.channel_id}>"

        title = Messages.LOG_MSG_EDIT.format(channel=channel_mention)

        if before_msg:
            if not self.should_log_user(before_msg.author, before_msg.guild):
                return
            
            # If the content didn't change (e.g. an embed was loaded), ignore
            if after_content is None or before_msg.content == after_content:
                return

            embed = self.create_base_embed(before_msg.author, title, Config.COLOR_WARNING)
            embed.add_field(name=Messages.FIELD_BEFORE, value=before_msg.content[:1024] or "*Empty*", inline=False)
            embed.add_field(name=Messages.FIELD_AFTER, value=after_content[:1024] or "*Empty*", inline=False)
            self.add_footer_info(embed, before_msg.author.id)
        else:
            # For uncached messages, we only know the new content (if provided)
            
            # Check author from raw payload to filter out bots
            author_data = payload.data.get("author", {})
            if author_data.get("bot"):
                if not Config.LOGGING.get("log_bots", False):
                    if str(author_data.get("id")) != str(self.bot.user.id) or not Config.LOGGING.get("log_self", False):
                        return

            # Avoid logging "Empty" edits
            if not after_content:
                return 

            archive_msg = None
            if Config.LOGGING.get("archive", {}).get("enabled", False):
                archive_msg = self.archive_db.get_message(payload.message_id)
                
            if archive_msg:
                if archive_msg['is_bot']:
                    if str(archive_msg['user_id']) == str(self.bot.user.id):
                        if not Config.LOGGING.get("log_self", True): return
                    else:
                        if not Config.LOGGING.get("log_bots", False): return

                before_content = archive_msg['content']
                before_author = archive_msg['username']
                before_user_id = archive_msg['user_id']
                
                # Check if content actually changed based on archive
                if before_content == after_content:
                    return
                # Update archive with new content
                self.archive_db.update_message_content(payload.message_id, after_content)
            else:
                before_content = "*Unknown (not cached & not in archive)*"
                before_author = None
                before_user_id = None

            embed = discord.Embed(
                description=title,
                color=Config.COLOR_WARNING,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text=f"Message ID: {payload.message_id}")
            if before_author:
                embed.set_author(name=f"@{before_author}")
                self.add_footer_info(embed, before_user_id)

            embed.add_field(name=Messages.FIELD_BEFORE, value=before_content[:1024] or "*Empty*", inline=False)
            embed.add_field(name=Messages.FIELD_AFTER, value=after_content[:1024] or "*Empty*", inline=False)

        await channel.send(embed=embed)

    # Member Events
    @commands.Cog.listener()
    async def on_member_join(self, member):
        channel = self.get_log_channel("member_join")
        if not channel: return

        title = Messages.LOG_MEMBER_JOIN.format(user=member.mention)
        embed = self.create_base_embed(member, title, Config.COLOR_SUCCESS)
        embed.add_field(name=Messages.FIELD_MEMBER_COUNT, value=str(member.guild.member_count), inline=True)
        embed.add_field(name=Messages.FIELD_CREATED_AT, value=discord.utils.format_dt(member.created_at, "R"), inline=True)
        
        self.add_footer_info(embed, member.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        channel = self.get_log_channel("member_leave")
        if not channel: return

        title = Messages.LOG_MEMBER_LEAVE.format(user=member.mention)
        embed = self.create_base_embed(member, title, Config.COLOR_DANGER)
        embed.add_field(name=Messages.FIELD_MEMBER_COUNT, value=str(member.guild.member_count), inline=True)
        
        self.add_footer_info(embed, member.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        channel = self.get_log_channel("member_ban")
        if not channel: return

        title = Messages.LOG_MEMBER_BAN.format(user=user.mention)
        embed = self.create_base_embed(user, title, Config.COLOR_DANGER)
        self.add_footer_info(embed, user.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        channel = self.get_log_channel("member_unban")
        if not channel: return

        title = Messages.LOG_MEMBER_UNBAN.format(user=user.mention)
        embed = self.create_base_embed(user, title, Config.COLOR_SUCCESS)
        self.add_footer_info(embed, user.id)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        channel = self.get_log_channel("member_update")
        if not channel: return

        title = Messages.LOG_MEMBER_UPDATE.format(user=after.mention)
        embed = self.create_base_embed(after, title, Config.COLOR_WARNING)
        changes = False

        if before.nick != after.nick:
            embed.add_field(name="Nickname", value=f"`{before.nick}` → `{after.nick}`", inline=False)
            changes = True

        if before.roles != after.roles:
            added = [role.mention for role in after.roles if role not in before.roles]
            removed = [role.mention for role in before.roles if role not in after.roles]
            if added:
                embed.add_field(name=Messages.FIELD_ROLES_ADDED, value=", ".join(added), inline=False)
                changes = True
            if removed:
                embed.add_field(name=Messages.FIELD_ROLES_REMOVED, value=", ".join(removed), inline=False)
                changes = True

        if not changes: return
        self.add_footer_info(embed, after.id)
        await channel.send(embed=embed)

    # Role Events
    @commands.Cog.listener()
    async def on_guild_role_create(self, role):
        channel = self.get_log_channel("role_create")
        if not channel: return

        user = await self.get_audit_log_user(role.guild, discord.AuditLogAction.role_create, role.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_ROLE_CREATE.format(role=role.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)
        
        embed.add_field(name=Messages.FIELD_NAME, value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        channel = self.get_log_channel("role_delete")
        if not channel: return

        user = await self.get_audit_log_user(role.guild, discord.AuditLogAction.role_delete, role.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_ROLE_DELETE.format(role=role.name)
        embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)

        embed.add_field(name="ID", value=role.id, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        channel = self.get_log_channel("role_update")
        if not channel: return

        if before.name == after.name and before.color == after.color and before.hoist == after.hoist and before.mentionable == after.mentionable:
            return

        user = await self.get_audit_log_user(after.guild, discord.AuditLogAction.role_update, after.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_ROLE_UPDATE.format(role=after.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)
        if before.name != after.name:
            embed.add_field(name=Messages.FIELD_NAME, value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.color != after.color:
            embed.add_field(name="Color", value=f"`{before.color}` → `{after.color}`", inline=False)
        
        await channel.send(embed=embed)

    # Emoji Events
    @commands.Cog.listener()
    async def on_guild_emojis_update(self, guild, before, after):
        channel_create = self.get_log_channel("emoji_create")
        channel_delete = self.get_log_channel("emoji_delete")
        channel_update = self.get_log_channel("emoji_update")

        # Created
        for emoji in after:
            if emoji not in before:
                if channel_create:
                    user = await self.get_audit_log_user(guild, discord.AuditLogAction.emoji_create, emoji.id)
                    if user and not self.should_log_user(user): continue
                    
                    title = Messages.LOG_EMOJI_CREATE.format(emoji=emoji)
                    embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
                    if user:
                        embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
                        self.add_footer_info(embed, user.id)
                    embed.add_field(name=Messages.FIELD_NAME, value=emoji.name, inline=True)
                    embed.add_field(name="ID", value=emoji.id, inline=True)
                    await channel_create.send(embed=embed)

        # Deleted
        for emoji in before:
            if emoji not in after:
                if channel_delete:
                    user = await self.get_audit_log_user(guild, discord.AuditLogAction.emoji_delete, emoji.id)
                    if user and not self.should_log_user(user): continue

                    title = Messages.LOG_EMOJI_DELETE.format(emoji=f":{emoji.name}:")
                    embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
                    if user:
                        embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
                        self.add_footer_info(embed, user.id)
                    embed.add_field(name="ID", value=emoji.id, inline=True)
                    await channel_delete.send(embed=embed)

        # Updated
        for a_emoji in after:
            for b_emoji in before:
                if a_emoji.id == b_emoji.id and a_emoji.name != b_emoji.name:
                    if channel_update:
                        user = await self.get_audit_log_user(guild, discord.AuditLogAction.emoji_update, a_emoji.id)
                        if user and not self.should_log_user(user): continue

                        title = Messages.LOG_EMOJI_UPDATE.format(emoji=a_emoji)
                        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
                        if user:
                            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
                            self.add_footer_info(embed, user.id)
                        embed.add_field(name="Name Change", value=f"`:{b_emoji.name}:` → `:{a_emoji.name}:`", inline=False)
                        await channel_update.send(embed=embed)

    # Channel Events
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = self.get_log_channel("channel_create")
        if not log_channel: return

        user = await self.get_audit_log_user(channel.guild, discord.AuditLogAction.channel_create, channel.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_CHAN_CREATE.format(channel=channel.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)

        embed.add_field(name=Messages.FIELD_NAME, value=channel.name, inline=True)
        embed.add_field(name=Messages.FIELD_TYPE, value=str(channel.type), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = self.get_log_channel("channel_delete")
        if not log_channel: return

        user = await self.get_audit_log_user(channel.guild, discord.AuditLogAction.channel_delete, channel.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_CHAN_DELETE.format(channel=channel.name)
        embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)

        embed.add_field(name=Messages.FIELD_TYPE, value=str(channel.type), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_channel = self.get_log_channel("channel_update")
        if not log_channel: return

        if before.name == after.name and before.category == after.category:
            return

        user = await self.get_audit_log_user(after.guild, discord.AuditLogAction.channel_update, after.id)
        if user and not self.should_log_user(user): return

        title = Messages.LOG_CHAN_UPDATE.format(channel=after.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if user:
            embed.set_author(name=f"@{user.name}", icon_url=user.display_avatar.url)
            self.add_footer_info(embed, user.id)
        if before.name != after.name:
            embed.add_field(name=Messages.FIELD_NAME, value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.category != after.category:
            embed.add_field(name=Messages.FIELD_CATEGORY, value=f"`{before.category}` → `{after.category}`", inline=False)
        
        await log_channel.send(embed=embed)

    # Voice Events
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.should_log_user(member, is_guild=True): return

        if before.channel is None and after.channel is not None:
            # Join
            channel = self.get_log_channel("voice_join")
            if channel:
                title = Messages.LOG_VOICE_JOIN.format(user=member.mention)
                embed = self.create_base_embed(member, title, Config.COLOR_SUCCESS)
                embed.add_field(name=Messages.FIELD_CHANNEL, value=after.channel.name, inline=True)
                embed.add_field(name=Messages.FIELD_MEMBER_COUNT, value=str(len(after.channel.members)), inline=True)
                self.add_footer_info(embed, member.id)
                await channel.send(embed=embed)

        elif before.channel is not None and after.channel is None:
            # Leave
            channel = self.get_log_channel("voice_leave")
            if channel:
                title = Messages.LOG_VOICE_LEAVE.format(user=member.mention)
                embed = self.create_base_embed(member, title, Config.COLOR_DANGER)
                embed.add_field(name=Messages.FIELD_CHANNEL, value=before.channel.name, inline=True)
                embed.add_field(name=Messages.FIELD_MEMBER_COUNT, value=str(len(before.channel.members)), inline=True)
                self.add_footer_info(embed, member.id)
                await channel.send(embed=embed)

        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            # Switch
            channel = self.get_log_channel("voice_switch")
            if channel:
                title = Messages.LOG_VOICE_SWITCH.format(user=member.mention)
                embed = self.create_base_embed(member, title, Config.COLOR_WARNING)
                embed.add_field(name=Messages.FIELD_FROM, value=before.channel.name, inline=True)
                embed.add_field(name=Messages.FIELD_TO, value=after.channel.name, inline=True)
                self.add_footer_info(embed, member.id)
                await channel.send(embed=embed)

    # Command Logs
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: discord.app_commands.Command or discord.app_commands.ContextMenu):
        channel = self.get_log_channel("command_logs")
        if not channel: return

        title = Messages.LOG_COMMAND_USED.format(command=command.name)
        embed = self.create_base_embed(interaction.user, title, Config.COLOR_PRIMARY)
        embed.add_field(name=Messages.FIELD_CHANNEL, value=interaction.channel.mention, inline=True)
        
        # Try to extract options if it's a slash command
        if hasattr(interaction, 'data') and 'options' in interaction.data:
            opts = []
            for opt in interaction.data['options']:
                val = opt.get('value')
                name = opt.get('name')
                opts.append(f"`{name}`: `{val}`")
            if opts:
                embed.add_field(name=Messages.FIELD_OPTIONS, value="\n".join(opts), inline=False)

        self.add_footer_info(embed, interaction.user.id)
        await channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
