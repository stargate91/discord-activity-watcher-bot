import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
import math
from config_loader import Config
from core.messages import Messages
from core.views import ModernInfoView, ModernDevInfoView, AltAccountModal
from core.visualizer import draw_peak_heatmap, draw_voice_usage_bars

def is_admin():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(ctx.author.roles, id=Config.ADMIN_ROLE_ID):
            return True
        return False
    return commands.check(predicate)

def is_admin_slash():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.ADMIN_ROLE_ID):
            return True
        return False
    return app_commands.check(predicate)

def is_tester_slash():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.ADMIN_ROLE_ID):
            return True
        if Config.TESTER_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.TESTER_ROLE_ID):
            return True
        return False
    return app_commands.check(predicate)

def is_tester():
    async def predicate(ctx):
        if ctx.author.guild_permissions.administrator:
            return True
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(ctx.author.roles, id=Config.ADMIN_ROLE_ID):
            return True
        if Config.TESTER_ROLE_ID != 0 and discord.utils.get(ctx.author.roles, id=Config.TESTER_ROLE_ID):
            return True
        return False
    return commands.check(predicate)

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
    @is_admin_slash()
    async def status_report(self, interaction: discord.Interaction):
        # Strict Admin Channel check
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
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
    @is_tester_slash()
    @app_commands.describe(
        type=Messages.CMD_SERVER_ANALYSIS_TYPE_DESC,
        timeframe=Messages.CMD_SERVER_ANALYSIS_TF_DESC
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Peak Activity Heatmap", value="peak"),
        app_commands.Choice(name="Voice Usage Ranking", value="voice"),
        app_commands.Choice(name="Voice Dedication (Longest Sessions)", value="dedication"),
        app_commands.Choice(name="Text Channel Activity", value="text_channels")
    ], timeframe=[
        app_commands.Choice(name="Weekly (7d)", value="7"),
        app_commands.Choice(name="Monthly (30d)", value="30"),
        app_commands.Choice(name="All-time", value="alltime")
    ])
    async def server_analysis(self, interaction: discord.Interaction, type: str, timeframe: str):
        # Accessible for everyone in Stats and Admin channel
        allowed_channels = [Config.ADMIN_CHANNEL_ID, Config.STATS_CHANNEL_ID]
        if 0 in allowed_channels: allowed_channels = [c for c in allowed_channels if c != 0]
        
        if interaction.channel_id not in allowed_channels:
            await interaction.response.send_message(
                Messages.ERR_PUBLIC_CHANNELS.format(admin_id=Config.ADMIN_CHANNEL_ID, stats_id=Config.STATS_CHANNEL_ID), 
                ephemeral=True
            )
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
            
        elif type == "dedication":
            raw_data = self.db.get_top_average_voice_duration(interaction.guild_id, days)
            if not raw_data:
                await interaction.followup.send(Messages.LB_EMPTY)
                return
            
            # Resolve user names
            formatted_data = []
            for uid, avg_mins in raw_data:
                member = interaction.guild.get_member(uid)
                name = member.display_name if member else f"Unknown ({uid})"
                formatted_data.append((name, avg_mins))
            
            output = f"dedication_{interaction.guild_id}.png"
            draw_voice_usage_bars(formatted_data, Messages.CHART_DEDICATION_TITLE.format(tf=tf_name), 
                                Messages.CHART_X_MIN_SESSION, "User", output)
            
            await interaction.followup.send(file=discord.File(output))
            if os.path.exists(output): os.remove(output)
            
        elif type == "text_channels":
            raw_data = self.db.get_channel_activity_raw(interaction.guild_id, days)
            if not raw_data:
                await interaction.followup.send(Messages.LB_EMPTY)
                return
                
            formatted_data = []
            for cid, total in raw_data:
                channel = interaction.guild.get_channel(cid)
                name = f"#{channel.name}" if channel else f"#{cid}"
                formatted_data.append((name, total))
                
            output = f"channels_{interaction.guild_id}.png"
            draw_voice_usage_bars(formatted_data, Messages.CHART_CHANNEL_TITLE.format(tf=tf_name), 
                                Messages.CHART_Y_MESSAGES, "Channel", output)
            
            await interaction.followup.send(file=discord.File(output))
            if os.path.exists(output): os.remove(output)

    @app_commands.command(name="game_details", description=Messages.CMD_GAME_DETAILS_DESC)
    @app_commands.describe(game=Messages.CMD_GAME_DETAILS_GAME_DESC)
    @is_tester_slash()
    async def game_details(self, interaction: discord.Interaction, game: str):
        # Restricted to Admin Channel
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        raw_data = self.db.get_game_top_players(interaction.guild_id, game)
        if not raw_data:
            await interaction.followup.send(Messages.GAME_REPORT_EMPTY, ephemeral=True)
            return
            
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
        header = Messages.GAME_DETAILS_HEADER
        line_sep = "-" * len(header)
        
        # Build report
        report_lines = [
            Messages.GAME_DETAILS_TITLE.format(game=game, guild=interaction.guild.name, now=now, header=header, line=line_sep)
        ]
        
        for i, (uid, mins, last_played) in enumerate(raw_data, 1):
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"Unknown ({uid})"
            last_dt = datetime.datetime.fromisoformat(last_played).strftime("%Y-%m-%d")
            report_lines.append(f"{i:2}. | {name:<30} | {int(mins):<10} | {last_dt}")
            
        filename = f"game_details_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))
            
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        if os.path.exists(filename): os.remove(filename)

    @game_details.autocomplete("game")
    async def game_details_autocomplete(self, interaction: discord.Interaction, current: str):
        games = self.db.get_all_unique_games(interaction.guild_id)
        return [
            app_commands.Choice(name=g, value=g)
            for g in games if current.lower() in g.lower()
        ][:25]

    @app_commands.command(name="stream_history", description=Messages.CMD_STREAM_HISTORY_DESC)
    @app_commands.describe(days=Messages.CMD_STREAM_HISTORY_DAYS_DESC)
    @is_tester_slash()
    async def stream_history(self, interaction: discord.Interaction, days: int = 7):
        # Accessible everywhere as per requirements
        await interaction.response.defer(ephemeral=True)
        
        history = self.db.get_stream_history(interaction.guild_id, days=days)
        if not history:
            await interaction.followup.send(Messages.STREAM_HISTORY_EMPTY, ephemeral=True)
            return

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"stream_history_{interaction.guild_id}_{now_str}.txt"
        
        # Header for the file
        title = f"--- STREAM HISTORY: {interaction.guild.name} (Last {days} days) ---\n"
        header = f"{'Timestamp':<20} | {'User':<25} | {'Duration':<10} | {'Stream Content'}\n"
        line = "-" * 80 + "\n"
        
        content = title + header + line
        
        for user_id, start_time, duration, detail, _ in history:
            user = interaction.guild.get_member(user_id)
            user_name = user.display_name if user else f"Unknown ({user_id})"
            
            # Format time
            try:
                dt = datetime.datetime.fromisoformat(start_time)
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = str(start_time)[:16]
                
            content += f"{time_str:<20} | {user_name:<25} | {int(duration):>3} min   | {detail}\n"
            
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
            
        await interaction.followup.send(
            Messages.STREAM_HISTORY_DONE.format(days=days, count=len(history)),
            file=discord.File(filename),
            ephemeral=True
        )
        
        # Clean up the file after sending
        if os.path.exists(filename):
            os.remove(filename)

    @app_commands.command(name="membership_logs", description=Messages.CMD_MEMBERSHIP_LOGS_DESC)
    @is_tester_slash()
    async def membership_logs(self, interaction: discord.Interaction):
        # Export join/leave history to TXT
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.send_message(Messages.MEMBERSHIP_LOG_GEN, ephemeral=True)
        
        try:
            logs = self.db.get_membership_logs(interaction.guild_id, limit=Config.REPORT_LOG_LIMIT)
            if not logs:
                await interaction.followup.send(Messages.MEMBERSHIP_LOG_EMPTY, ephemeral=True)
                return
            
            lines = [f"--- MEMBERSHIP LOG: {interaction.guild.name} ---", f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
            lines.append(f"{'Timestamp':<20} | {'User ID':<20} | {'Username':<25} | {'Action':<10}")
            lines.append("-" * 80)
            
            for uid, action, ts in logs:
                m = interaction.guild.get_member(uid)
                name = str(m) if m else Messages.LB_UNKNOWN_USER.format(id=uid)
                # ts is isoformat from db
                display_ts = ts[:19].replace('T', ' ')
                lines.append(f"{display_ts:<20} | {uid:<20} | {name[:25]:<25} | {action:<10}")
            
            filename = f"membership_log_{interaction.guild_id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            await interaction.followup.send(
                content=Messages.MEMBERSHIP_LOG_DONE.format(count=len(logs)),
                file=discord.File(filename), 
                ephemeral=True
            )
            os.remove(filename)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="game_role_report", description=Messages.CMD_GAME_ROLE_REPORT_DESC)
    @is_tester_slash()
    async def game_role_report(self, interaction: discord.Interaction):
        # This command creates a report showing when the bot gave or took away game roles
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
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
    @is_admin_slash()
    async def reset_database(self, interaction: discord.Interaction):
        # DANGER: This command deletes ALL stats from the database!
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        try:
            self.db.reset_database()
            await interaction.response.send_message(Messages.DB_RESET_SUCCESS, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(Messages.DB_RESET_ERROR.format(e=e), ephemeral=True)

    @commands.command(name=f"sync{Config.SUFFIX}", help=Messages.CMD_SYNC_DESC)
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

    @commands.command(name=f"clear_commands{Config.SUFFIX}", help=Messages.CMD_CLEAR_HELP)
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
    @is_admin_slash()
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

    @commands.command(name=f"info{Config.SUFFIX}", help=Messages.CMD_INFO_DESC)
    @is_admin()
    async def info_prefix(self, ctx: commands.Context):
        # Dual-channel check: Stats or Admin channel
        if Config.STATS_CHANNEL_ID != 0 and ctx.channel.id != Config.STATS_CHANNEL_ID and ctx.channel.id != Config.ADMIN_CHANNEL_ID:
            await ctx.send(Messages.ERR_PUBLIC_CHANNELS.format(admin_id=Config.ADMIN_CHANNEL_ID, stats_id=Config.STATS_CHANNEL_ID))
            return

        # This command posts the bot's introduction card to the stats channel
        stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
        if not stats_channel:
            await ctx.send(Messages.ERR_STATS_NOT_FOUND)
            return
            
        view = ModernInfoView(ctx.guild)
        await stats_channel.send(view=view)

    @app_commands.command(name="info", description=Messages.CMD_INFO_DESC)
    @is_admin_slash()
    async def info_slash(self, interaction: discord.Interaction):
        # Matches !info specifications
        # Matches !info specifications - Allowed in Stats or Admin channel
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(
                Messages.ERR_PUBLIC_CHANNELS.format(admin_id=Config.ADMIN_CHANNEL_ID, stats_id=Config.STATS_CHANNEL_ID), 
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=False) # Info can be public once triggered in correct channel

        view = ModernInfoView(interaction.guild)
        await interaction.followup.send(view=view)

    @commands.command(name=f"info_dev{Config.SUFFIX}", help=Messages.CMD_INFO_DEV_DESC)
    @is_tester()
    async def info_dev_prefix(self, ctx: commands.Context):
        # Restricted to Admin Channel but no role requirement
        if Config.ADMIN_CHANNEL_ID != 0 and ctx.channel.id != Config.ADMIN_CHANNEL_ID:
            await ctx.send(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID))
            return
        
        await self._send_dev_help(ctx)

    @app_commands.command(name="info_dev", description=Messages.CMD_INFO_DEV_DESC)
    @is_tester_slash()
    async def info_dev_slash(self, interaction: discord.Interaction):
        # Dev help is for Admins only
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await self._send_dev_help(interaction)

    async def _send_dev_help(self, target):
        prefix_cmds = []
        for cmd in self.bot.commands:
            prefix_cmds.append((cmd.name, Config.format_desc(cmd.help or "---", target.guild if hasattr(target, "guild") else target)))
            
        # 3. Slash Commands Section
        # We categorize them by their required role/access level for clarity
        slash_cmds = []
        for cmd in self.bot.tree.get_commands():
            if isinstance(cmd, app_commands.Group):
                for sub in cmd.commands:
                    full_name = f"{cmd.name} {sub.name}"
                    access_info = self._get_command_access_info(full_name)
                    slash_cmds.append((full_name, Config.format_desc(sub.description, target.guild if hasattr(target, "guild") else target), access_info))
            else:
                access_info = self._get_command_access_info(cmd.name)
                slash_cmds.append((cmd.name, Config.format_desc(cmd.description, target.guild if hasattr(target, "guild") else target), access_info))

        view = ModernDevInfoView(target.guild if isinstance(target, commands.Context) else target.guild, prefix_cmds, slash_cmds)
        
        if isinstance(target, commands.Context):
            await target.send(view=view)
        else:
            await target.response.send_message(view=view)

    def _get_command_access_info(self, name):
        """Returns a string describing the role and channel requirements for a command."""
        from core.ui_icons import Icons
        
        # Role Requirements
        admin_cmds = ["membership_logs", "game_role_report", "reset_database", "sync", "link_alt", "add_game", "remove_game", "test_weekly_layout"]
        tester_cmds = ["status_report", "game_details", "list_games", "game_stats_report", "info_dev", "champion_log", "server_analysis", "info"]
        
        icon_role = Icons.ROLE_USER
        label_role = Messages.HELP_ROLE_EVERYONE
        
        if name in admin_cmds: 
            icon_role = Icons.ROLE_ADMIN
            label_role = Messages.HELP_ROLE_ADMIN
        elif name in tester_cmds: 
            icon_role = Icons.ROLE_TESTER
            label_role = Messages.HELP_ROLE_TESTER
        
        # Channel Requirements
        admin_ch_cmds = admin_cmds + ["status_report", "game_details", "list_games", "game_stats_report", "info_dev"]
        stats_ch_cmds = ["top", "server_analysis", "champion_log", "info"]
        any_ch_cmds = ["stream_history", "me"]
        
        icon_chan = Icons.CHAN_ANY
        label_chan = Messages.HELP_CHAN_ANY
        
        if name in any_ch_cmds:
            icon_chan = Icons.CHAN_ANY
            label_chan = Messages.HELP_CHAN_ANY
        elif name in admin_ch_cmds: 
            icon_chan = Icons.CHAN_ADMIN
            label_chan = Messages.HELP_CHAN_ADMIN
        elif name in stats_ch_cmds: 
            # These are allowed in both, but primarily 'Public'
            icon_chan = Icons.CHAN_STATS
            label_chan = Messages.HELP_CHAN_STATS
        
        return f"{icon_role} {label_role} | {icon_chan} {label_chan}"

    @app_commands.command(name="link_alt", description=Messages.CMD_LINK_ALT_DESC)
    @is_admin_slash()
    async def link_alt(self, interaction: discord.Interaction):
        # This command opens the modal to link an alt account to a main account
        if interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.send_modal(AltAccountModal())

    def refresh_descriptions(self, guild):
        """Re-formats all slash command descriptions using actual names from the guild."""
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
