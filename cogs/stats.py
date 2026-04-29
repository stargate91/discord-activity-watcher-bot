import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages
from core.views import ModernLeaderboardView, ModernProfileView
from core.visualizer import draw_user_activity_chart
from core.logger import log

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.engine = bot.engine

    def _can_toggle_command(self, interaction: discord.Interaction, cmd_name: str) -> bool:
        """Checks if a user has permission to make a specific command's response public."""
        if interaction.user.guild_permissions.administrator: return True
            
        settings = Config.COMMAND_SETTINGS.get(cmd_name, {})
        req_role = settings.get("toggle_role", "ADMIN")
        
        if req_role == "EVERYONE": return True
        if req_role == "ADMIN":
            return Config.ADMIN_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.ADMIN_ROLE_ID) is not None
        if req_role == "TESTER":
            if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.ADMIN_ROLE_ID) is not None:
                return True
            return Config.TESTER_ROLE_ID != 0 and discord.utils.get(interaction.user.roles, id=Config.TESTER_ROLE_ID) is not None
        return False

    def refresh_descriptions(self, guild):
        bname = self.bot.user.name if self.bot.user else "Iris"
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild, bot_name=bname)

    @app_commands.command(name="top", description=Messages.CMD_TOP_DESC)
    @app_commands.describe(timeframe=Messages.CMD_TOP_TF_DESC)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def top(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        await interaction.response.defer(ephemeral=True)
        try:
            top_10, u_stats = await self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
            view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
            await interaction.followup.send(view=view, ephemeral=True)
        except Exception as e:
            log.error(f"Error in top command: {e}", exc_info=True)
            await interaction.followup.send(Messages.ERR_STATS_LOAD.format(e=e), ephemeral=True)

    async def _prepare_profile(self, interaction, target_user, main_id, timeframe="me", static=False, shared_by=None):
        _, user_full_stats = await self.bot.engine.get_leaderboard(
            interaction.guild, 
            user=target_user, 
            live_voice_times=self.bot.voice_start_times,
            timeframe="alltime" if timeframe == "me" else timeframe
        )
        
        if not user_full_stats: return None, None
        user, data, points, voice_mins, rank = user_full_stats
        
        social = await self.db.get_user_social_stats(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        partners = await self.db.get_top_voice_partners(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        top_games = await self.db.get_user_top_games(main_id, interaction.guild_id, limit=3)
        
        monthly_data = await self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        user_monthly = monthly_data.get(main_id, {"messages":0})
        avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
        avg_voice = await self.db.get_user_average_voice_duration(main_id, interaction.guild_id)
        
        joined_at = await self.db.get_user_join_date(main_id, interaction.guild_id)
        tenure_days = (datetime.datetime.now(datetime.timezone.utc) - joined_at.replace(tzinfo=datetime.timezone.utc)).days if joined_at else 0
        efficiency = points / (tenure_days + 1) if tenure_days >= 0 else points
        
        chart_file = None
        chart_url = None
        daily_activity = await self.db.get_user_daily_activity(main_id, interaction.guild_id, days=7)
        
        if daily_activity and main_id in self.bot.voice_start_times:
            row = daily_activity[-1]
            d_str, d_points, d_voice = row[0], row[1], row[2]
            start = self.bot.voice_start_times[main_id]
            multiplier, is_streaming, _ = self.bot.voice_multipliers.get(main_id, (Config.POINTS_VOICE, False, None))
            now_utc = datetime.datetime.now(datetime.timezone.utc)
            live_mins = (now_utc - start).total_seconds() / 60
            live_points = live_mins * multiplier
            daily_activity[-1] = (d_str, d_points + live_points, d_voice + live_mins)

        if daily_activity:
            os.makedirs(Config.TEMP_DIR, exist_ok=True)
            path = os.path.join(Config.TEMP_DIR, f"profile_{main_id}_{int(datetime.datetime.now().timestamp())}.png")
            draw_user_activity_chart(
                daily_activity, 
                f"Activity: {user.display_name}", 
                points_label=Messages.VIS_POINTS,
                voice_label=Messages.VIS_VOICE_MINS,
                y_points_label=Messages.VIS_ACTIVITY_POINTS,
                y_voice_label=Messages.VIS_VOICE_MINUTES,
                output_path=path
            )
            if os.path.exists(path):
                chart_file = discord.File(path, filename="chart.png")
                chart_url = "attachment://chart.png"

        view = ModernProfileView(user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, 
                                 joined_at=joined_at, tenure_days=tenure_days, efficiency=efficiency, chart_url=chart_url, 
                                 timeframe=timeframe, static=static, shared_by=shared_by)
        return view, chart_file

    @app_commands.command(name="me", description=Messages.CMD_ME_MEMBER_DESC)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def me(self, interaction: discord.Interaction):
        target = interaction.user
        main_id = Config.get_main_id(target.id)
        main_member = interaction.guild.get_member(main_id) or target
        await interaction.response.defer(ephemeral=True)
        try:
            view, chart_file = await self._prepare_profile(interaction, main_member, main_id)
            if not view:
                await interaction.followup.send(Messages.ERR_NO_DATA, ephemeral=True)
                return
            await interaction.followup.send(view=view, file=chart_file, ephemeral=True) if chart_file else await interaction.followup.send(view=view, ephemeral=True)
        except Exception as e:
            log.error(f"Error in me command: {e}", exc_info=True)
            await interaction.followup.send(Messages.ERR_STATS_LOAD.format(e=e), ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("top:"):
                parts = custom_id.split(":")
                current_tf = parts[1] if len(parts) >= 2 else "alltime"
                action = parts[2] if len(parts) >= 3 else parts[1]
                
                view = None
                chart_file = None

                if action in ["weekly", "monthly", "alltime"]:
                    top_10, u_stats = await self.bot.get_top_data(interaction.guild, interaction.user, action)
                    view = ModernLeaderboardView(top_10, action, interaction.guild, u_stats)
                elif action == "show_me":
                    main_id = Config.get_main_id(interaction.user.id)
                    main_member = interaction.guild.get_member(main_id) or interaction.user
                    view, chart_file = await self._prepare_profile(interaction, main_member, main_id)
                    if not view:
                        await interaction.response.send_message(Messages.ERR_NO_DATA_PERIOD, ephemeral=True)
                        return
                elif action == "share":
                    cmd_name = "me" if current_tf == "me" else "top"
                    if not self._can_toggle_command(interaction, cmd_name):
                        await interaction.response.send_message(Messages.ERR_NO_PERMISSION, ephemeral=True)
                        return
                    if current_tf == "me":
                        main_id = Config.get_main_id(interaction.user.id)
                        main_member = interaction.guild.get_member(main_id) or interaction.user
                        view_shared, chart_file = await self._prepare_profile(interaction, main_member, main_id, static=True, shared_by=interaction.user.display_name)
                    else:
                        top_10, u_stats = await self.bot.get_top_data(interaction.guild, interaction.user, current_tf)
                        view_shared = ModernLeaderboardView(top_10, current_tf, interaction.guild, u_stats, static=True, shared_by=interaction.user.display_name)
                    target_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID) or interaction.channel
                    await target_channel.send(view=view_shared, file=chart_file) if chart_file else await target_channel.send(view=view_shared)
                    await interaction.response.send_message(Messages.SUCCESS_SHARED, ephemeral=True)
                    return
                
                if view:
                    if action == "show_me":
                        await interaction.response.send_message(view=view, file=chart_file, ephemeral=True) if chart_file else await interaction.response.send_message(view=view, ephemeral=True)
                    else: await interaction.response.edit_message(view=view)
    
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(Messages.ERR_COOLDOWN.format(retry_after=error.retry_after), ephemeral=True)
        else: raise error

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
