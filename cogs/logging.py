import discord
from discord.ext import commands
import datetime
from config_loader import Config
from core.logger import log
from core.messages import Messages

class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

    # Message Events
    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        channel = self.get_log_channel("message_delete")
        if not channel: return

        message = payload.cached_message
        channel_obj = self.bot.get_channel(payload.channel_id)
        channel_mention = channel_obj.mention if channel_obj else f"<#{payload.channel_id}>"

        if message:
            if not message.guild or message.author.bot:
                if not Config.LOGGING.get("log_self", True) or (message.author != self.bot.user):
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
            embed.add_field(name="Content", value="*Message content unknown (not cached)*", inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        channel = self.get_log_channel("message_edit")
        if not channel: return

        # Raw payload might not have 'content' if it wasn't modified or if it's not cached
        before_msg = payload.cached_message
        
        # 'payload.data' contains the new state of the message
        after_content = payload.data.get("content")
        channel_obj = self.bot.get_channel(payload.channel_id)
        channel_mention = channel_obj.mention if channel_obj else f"<#{payload.channel_id}>"

        title = Messages.LOG_MSG_EDIT.format(channel=channel_mention)

        if before_msg:
            if not before_msg.guild or before_msg.author.bot:
                if not Config.LOGGING.get("log_self", True) or (before_msg.author != self.bot.user):
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
            # We don't have the "before" state
            if after_content is None:
                return # Can't log an edit if we have no new content
            embed = discord.Embed(
                description=title,
                color=Config.COLOR_WARNING,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            embed.set_footer(text=f"Message ID: {payload.message_id}")
            embed.add_field(name=Messages.FIELD_BEFORE, value="*Unknown (not cached)*", inline=False)
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

        title = Messages.LOG_ROLE_CREATE.format(role=role.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name=Messages.FIELD_NAME, value=role.name, inline=True)
        embed.add_field(name="ID", value=role.id, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role):
        channel = self.get_log_channel("role_delete")
        if not channel: return

        title = Messages.LOG_ROLE_DELETE.format(role=role.name)
        embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name="ID", value=role.id, inline=True)
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_role_update(self, before, after):
        channel = self.get_log_channel("role_update")
        if not channel: return

        if before.name == after.name and before.color == after.color and before.hoist == after.hoist and before.mentionable == after.mentionable:
            return

        title = Messages.LOG_ROLE_UPDATE.format(role=after.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
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
                    title = Messages.LOG_EMOJI_CREATE.format(emoji=emoji)
                    embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
                    embed.add_field(name=Messages.FIELD_NAME, value=emoji.name, inline=True)
                    embed.add_field(name="ID", value=emoji.id, inline=True)
                    await channel_create.send(embed=embed)

        # Deleted
        for emoji in before:
            if emoji not in after:
                if channel_delete:
                    title = Messages.LOG_EMOJI_DELETE.format(emoji=f":{emoji.name}:")
                    embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
                    embed.add_field(name="ID", value=emoji.id, inline=True)
                    await channel_delete.send(embed=embed)

        # Updated
        for a_emoji in after:
            for b_emoji in before:
                if a_emoji.id == b_emoji.id and a_emoji.name != b_emoji.name:
                    if channel_update:
                        title = Messages.LOG_EMOJI_UPDATE.format(emoji=a_emoji)
                        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
                        embed.add_field(name="Name Change", value=f"`:{b_emoji.name}:` → `:{a_emoji.name}:`", inline=False)
                        await channel_update.send(embed=embed)

    # Channel Events
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        log_channel = self.get_log_channel("channel_create")
        if not log_channel: return

        title = Messages.LOG_CHAN_CREATE.format(channel=channel.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_SUCCESS, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name=Messages.FIELD_NAME, value=channel.name, inline=True)
        embed.add_field(name=Messages.FIELD_TYPE, value=str(channel.type), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        log_channel = self.get_log_channel("channel_delete")
        if not log_channel: return

        title = Messages.LOG_CHAN_DELETE.format(channel=channel.name)
        embed = discord.Embed(description=title, color=Config.COLOR_DANGER, timestamp=datetime.datetime.now(datetime.timezone.utc))
        embed.add_field(name=Messages.FIELD_TYPE, value=str(channel.type), inline=True)
        await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_channel_update(self, before, after):
        log_channel = self.get_log_channel("channel_update")
        if not log_channel: return

        if before.name == after.name and before.category == after.category:
            return

        title = Messages.LOG_CHAN_UPDATE.format(channel=after.mention)
        embed = discord.Embed(description=title, color=Config.COLOR_WARNING, timestamp=datetime.datetime.now(datetime.timezone.utc))
        if before.name != after.name:
            embed.add_field(name=Messages.FIELD_NAME, value=f"`{before.name}` → `{after.name}`", inline=False)
        if before.category != after.category:
            embed.add_field(name=Messages.FIELD_CATEGORY, value=f"`{before.category}` → `{after.category}`", inline=False)
        
        await log_channel.send(embed=embed)

    # Voice Events
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return

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
