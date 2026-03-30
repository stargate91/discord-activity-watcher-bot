import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import math
from config_loader import Config
from core.messages import Messages
from core.views import ModernInfoView, ModernDevInfoView
from core.visualizer import draw_peak_heatmap, draw_voice_usage_bars

def is_admin():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(ctx.author.roles, id=Config.ADMIN_ROLE_ID):
            return True
        return False
    return commands.check(predicate)

def is_admin_interaction():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.ADMIN_ROLE_ID):
            return True
        return False
    return app_commands.check(predicate)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        
        # Initial format (placeholders to IDs)
        for cmd in self.get_app_commands():
             if not hasattr(cmd, "_raw_desc"):
                 cmd._raw_desc = cmd.description
             cmd.description = Config.format_desc(cmd._raw_desc)

    @app_commands.command(name="status_report", description=Messages.CMD_STATUS_REPORT_DESC)
    async def status_report(self, interaction: discord.Interaction):
        # Check if we are in the right channel to use admin commands
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.send_message(Messages.REPORT_GEN_STATUS, ephemeral=True)
        # Start building a text report with everyone's stats
        now = datetime.datetime.now(datetime.timezone.utc)
        guild_data = self.db.get_all_guild_data(interaction.guild_id)
        r1, r2 = interaction.guild.get_role(Config.STAGE_1_ROLE_ID), interaction.guild.get_role(Config.STAGE_2_ROLE_ID)
        lines = [Messages.REPORT_TITLE_HEADER.format(guild=interaction.guild.name, now=now)]
        
        # Go through every person in the server and add their numbers to the list
        for m in interaction.guild.members:
            if m.bot: continue
            
            main_id = Config.get_main_id(m.id)
            is_alt = main_id != m.id
            d = guild_data.get(main_id)
            if not d: continue

            name_display = str(m)[:25]
            if is_alt:
                main_m = interaction.guild.get_member(main_id)
                main_name = str(main_m)[:15] if main_m else f"{main_id} - left"
                name_display = f"{name_display} (Main: {main_name})"
            
            voice_mins = d['voice_minutes']
            if main_id in self.bot.voice_start_times:
                voice_mins += (now - self.bot.voice_start_times[main_id]).total_seconds() / 60
                
            s = Messages.REPORT_STAGE_NORMAL
            if r1 in m.roles: s = Messages.REPORT_STAGE_1
            elif r2 in m.roles: s = Messages.REPORT_STAGE_2
            
            if s == Messages.REPORT_STAGE_1:
                det = Messages.REPORT_INACTIVE
            elif s == Messages.REPORT_STAGE_2 and d["returned_at"]:
                diff = (now - d['returned_at'].astimezone(datetime.timezone.utc)).total_seconds()
                days_left = math.ceil((Config.STAGE_2_GRACE_DAYS * 86400 - diff) / 86400)
                det = Messages.REPORT_S2_RETURN.format(days=max(0, days_left))
            else:
                diff = (now - d['last_active'].astimezone(datetime.timezone.utc)).total_seconds()
                days_left = math.ceil((Config.STAGE_1_DAYS * 86400 - diff) / 86400)
                det = Messages.REPORT_S1_LIMIT.format(days=max(0, days_left))

            lines.append(f"{name_display:<35} | {s:<12} | {d['message_count']:<4} | {d['reaction_count']:<4} | {int(voice_mins):<4} | {det}")
        
        # Save everything into a .txt file and send it to the admin
        filename = f"report_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        # Delete the file from the computer after sending it
        os.remove(filename)

    @app_commands.command(name="server_analysis", description=Messages.CMD_SERVER_ANALYSIS_DESC)
    @app_commands.describe(
        type=Messages.CMD_SERVER_ANALYSIS_TYPE_DESC,
        timeframe=Messages.CMD_SERVER_ANALYSIS_TF_DESC
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Peak Activity Heatmap", value="peak"),
        app_commands.Choice(name="Voice Usage Ranking", value="voice")
    ], timeframe=[
        app_commands.Choice(name="Weekly (7d)", value="7"),
        app_commands.Choice(name="Monthly (30d)", value="30"),
        app_commands.Choice(name="All-time", value="alltime")
    ])
    @is_admin_interaction()
    async def server_analysis(self, interaction: discord.Interaction, type: str, timeframe: str):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        days = int(timeframe) if timeframe != "alltime" else None
        # Handle timeframe name for title
        tf_name = timeframe if timeframe == "alltime" else f"{timeframe}d"
        
        if type == "peak":
            data = self.db.get_peak_activity_raw(interaction.guild_id, days)
            if not data:
                await interaction.followup.send(Messages.LB_EMPTY)
                return
            
            day_names = [getattr(Messages, f"DAY_{i}") for i in range(7)]
            output = f"peak_{interaction.guild_id}.png"
            draw_peak_heatmap(data, Messages.CHART_PEAK_TITLE.format(tf=tf_name), 
                            Messages.CHART_X_HOUR, Messages.CHART_Y_DAY, day_names, output)
            
            await interaction.followup.send(file=discord.File(output))
            if os.path.exists(output): os.remove(output)
            
        elif type == "voice":
            raw_data = self.db.get_voice_usage_raw(interaction.guild_id, days)
            if not raw_data:
                await interaction.followup.send(Messages.LB_EMPTY)
                return
            
            # Resolve channel names
            formatted_data = []
            for cid, mins in raw_data:
                ch = interaction.guild.get_channel(cid)
                name = ch.name if ch else f"Unknown ({cid})"
                formatted_data.append((name, mins))
            
            output = f"voice_{interaction.guild_id}.png"
            # Switch axes description for bar chart: x is minutes, y is Channel
            draw_voice_usage_bars(formatted_data, Messages.CHART_VOICE_TITLE.format(tf=tf_name), 
                                Messages.CHART_Y_MINUTES, "Channel", output)
            
            await interaction.followup.send(file=discord.File(output))
            if os.path.exists(output): os.remove(output)

    @app_commands.command(name="game_role_report", description=Messages.CMD_GAME_ROLE_REPORT_DESC)
    async def game_role_report(self, interaction: discord.Interaction):
        # This command creates a report showing when the bot gave or took away game roles
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
        
        await interaction.response.send_message(Messages.REPORT_GEN_ROLE, ephemeral=True)
        
        history = self.db.get_role_history(interaction.guild_id, limit=Config.REPORT_LOG_LIMIT)
        if not history:
            await interaction.followup.send(Messages.REPORT_EMPTY_HISTORY, ephemeral=True)
            return

        now_utc = datetime.datetime.now(datetime.timezone.utc)
        lines = [Messages.ROLE_LOG_TITLE.format(guild=interaction.guild.name, now=now_utc)]
        
        for uid, role, action, ts in history:
            m = interaction.guild.get_member(uid)
            name = str(m) if m else Messages.LB_UNKNOWN_USER.format(id=uid)
            act_text = Messages.ROLE_LOG_REMOVED if action == 'REMOVED' else Messages.ROLE_LOG_ADDED
            lines.append(f"{ts[:19]:<20} | {name[:25]:<25} | {act_text:<10} | {role}")
        
        filename = f"role_log_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        os.remove(filename)

    @app_commands.command(name="reset_database", description=Messages.CMD_RESET_DB_DESC)
    @is_admin_interaction()
    async def reset_database(self, interaction: discord.Interaction):
        # DANGER: This command deletes ALL stats from the database!
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        try:
            self.db.reset_database()
            await interaction.response.send_message(Messages.DB_RESET_SUCCESS, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(Messages.DB_RESET_ERROR.format(e=e), ephemeral=True)

    @commands.command(name=f"sync{Config.SUFFIX}")
    @commands.guild_only()
    @is_admin()
    async def sync_prefix(self, ctx: commands.Context, spec: str | None = None):
        # Refresh descriptions before syncing
        for cog in self.bot.cogs.values():
            if hasattr(cog, "refresh_descriptions"):
                cog.refresh_descriptions(ctx.guild)

        # Only check the channel if the user has permission
        if Config.ADMIN_CHANNEL_ID != 0 and ctx.channel.id != Config.ADMIN_CHANNEL_ID:
            await ctx.send(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID))
            return
            
        if spec == "global":
            synced = await self.bot.tree.sync()
            await ctx.send(f"Synced {len(synced)} commands globally.")
        elif spec == "copy":
            self.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Copied global and synced {len(synced)} commands to this guild.")
        else:
            # Sync commands only for this specific server (guild)
            synced = await self.bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"Synced {len(synced)} commands to this guild.")

    @commands.command(name=f"clear_commands{Config.SUFFIX}")
    @commands.guild_only()
    @is_admin()
    async def clear_commands_prefix(self, ctx: commands.Context):
        # This part removes all the slash commands from Discord for this bot
        if Config.ADMIN_CHANNEL_ID != 0 and ctx.channel.id != Config.ADMIN_CHANNEL_ID:
            await ctx.send(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID))
            return
            
        # Global clear
        self.bot.tree.clear_commands(guild=None)
        await self.bot.tree.sync(guild=None)
        
        # Guild clear
        self.bot.tree.clear_commands(guild=ctx.guild)
        await self.bot.tree.sync(guild=ctx.guild)
        
        await ctx.send(Messages.CMD_CLEAR_DONE.format(cmd=f"{Config.PREFIX}sync{Config.SUFFIX}"))

    @app_commands.command(name="sync", description=Messages.CMD_SYNC_DESC)
    @app_commands.describe(mode=Messages.CMD_SYNC_MODE_DESC)
    @is_admin_interaction()
    async def sync_slash(self, interaction: discord.Interaction, mode: str = "guild"):
        # Refresh descriptions before syncing
        for cog in self.bot.cogs.values():
            if hasattr(cog, "refresh_descriptions"):
                cog.refresh_descriptions(interaction.guild)

        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        if mode == "global":
            synced = await self.bot.tree.sync()
            await interaction.followup.send(f"Synced {len(synced)} commands globally.")
        elif mode == "copy":
            self.bot.tree.copy_global_to(guild=interaction.guild)
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"Copied global and synced {len(synced)} commands to this guild.")
        else:
            synced = await self.bot.tree.sync(guild=interaction.guild)
            await interaction.followup.send(f"Synced {len(synced)} commands to this guild.")

    @commands.command(name=f"info{Config.SUFFIX}")
    @is_admin()
    async def info_prefix(self, ctx: commands.Context):
        # This command must only be used in the stats channel
        if Config.STATS_CHANNEL_ID != 0 and ctx.channel.id != Config.STATS_CHANNEL_ID:
            await ctx.send(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID))
            return

        # This command posts the bot's introduction card to the stats channel
        stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
        if not stats_channel:
            await ctx.send(Messages.ERR_STATS_NOT_FOUND)
            return
            
        view = ModernInfoView(ctx.guild)
        await stats_channel.send(view=view)

    @app_commands.command(name="info", description=Messages.CMD_INFO_DESC)
    @is_admin_interaction()
    async def info_slash(self, interaction: discord.Interaction):
        # Matches !info specifications
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID), ephemeral=True)
            return

        view = ModernInfoView(interaction.guild)
        await interaction.response.send_message(view=view)

    @commands.command(name=f"info_dev{Config.SUFFIX}")
    async def info_dev_prefix(self, ctx: commands.Context):
        # Restricted to Admin Channel but no role requirement
        if Config.ADMIN_CHANNEL_ID != 0 and ctx.channel.id != Config.ADMIN_CHANNEL_ID:
            await ctx.send(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID))
            return
        
        await self._send_dev_help(ctx)

    @app_commands.command(name="info_dev", description=Messages.CMD_INFO_DEV_DESC)
    async def info_dev_slash(self, interaction: discord.Interaction):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await self._send_dev_help(interaction)

    async def _send_dev_help(self, target):
        prefix_cmds = []
        prefix_map = {
            f"sync{Config.SUFFIX}": Messages.CMD_SYNC_DESC,
            f"clear_commands{Config.SUFFIX}": Messages.CMD_CLEAR_HELP,
            f"info{Config.SUFFIX}": Messages.CMD_INFO_DESC,
            f"info_dev{Config.SUFFIX}": Messages.CMD_INFO_DEV_DESC
        }
        
        for cmd in self.bot.commands:
            help_text = prefix_map.get(cmd.name, cmd.help)
            prefix_cmds.append((cmd.name, Config.format_desc(help_text, target.guild if isinstance(target, commands.Context) else target.guild)))
            
        slash_cmds = []
        for cmd in self.bot.tree.get_commands():
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    slash_cmds.append((f"{cmd.name} {sub.name}", Config.format_desc(sub.description, target.guild if hasattr(target, "guild") else target)))
            else:
                slash_cmds.append((cmd.name, Config.format_desc(cmd.description, target.guild if hasattr(target, "guild") else target)))

        view = ModernDevInfoView(target.guild if isinstance(target, commands.Context) else target.guild, prefix_cmds, slash_cmds)
        
        if isinstance(target, commands.Context):
            await target.send(view=view)
        else:
            await target.response.send_message(view=view)

    def refresh_descriptions(self, guild):
        """Re-formats all slash command descriptions using actual names from the guild."""
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
