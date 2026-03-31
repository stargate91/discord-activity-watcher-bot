import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages
from core.views import ModernLeaderboardView, ModernProfileView
from core.visualizer import draw_user_activity_chart

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.engine = bot.engine
        
        # Initial format (placeholders to IDs)
        for cmd in self.get_app_commands():
             if not hasattr(cmd, "_raw_desc"):
                 cmd._raw_desc = cmd.description
             cmd.description = Config.format_desc(cmd._raw_desc)

    def refresh_descriptions(self, guild):
        """Re-formats all slash command descriptions using actual names from the guild."""
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild)

    @app_commands.command(name="top", description=Messages.CMD_TOP_DESC)
    @app_commands.describe(timeframe=Messages.CMD_TOP_TF_DESC)
    @app_commands.checks.cooldown(1, 10.0, key=lambda i: (i.guild_id, i.user.id))
    async def top(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        # This command shows the Top 10 leaderboard (highest scores) for the server
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID), ephemeral=True)
            return

        top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
        view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
        await interaction.response.send_message(view=view, ephemeral=True)

    async def _prepare_profile(self, interaction, target_user, main_id, timeframe="me", static=False, shared_by=None):
        """Helper to fetch stats, generate chart and prepare ModernProfileView."""
        # Use the main_id for stat retrieval
        _, user_full_stats = self.bot.engine.get_leaderboard(
            interaction.guild, 
            user=target_user, 
            live_voice_times=self.bot.voice_start_times,
            timeframe="alltime" if timeframe == "me" else timeframe
        )
        
        if not user_full_stats:
            return None, None

        # user_full_stats contains (user, data, points, voice_mins, rank)
        user, data, points, voice_mins, rank = user_full_stats
        
        # Calculate extra social stats (who they talk to most, favorite emoji, etc.)
        social = self.db.get_user_social_stats(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        partners = self.db.get_top_voice_partners(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        top_games = self.db.get_user_top_games(main_id, interaction.guild_id, limit=3)
        
        # Calculate Daily Average (30 days)
        monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        user_monthly = monthly_data.get(main_id, {"messages":0})
        avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
        avg_voice = self.db.get_user_average_voice_duration(main_id, interaction.guild_id)
        
        # Veteran Stats
        joined_at = self.db.get_user_join_date(main_id, interaction.guild_id)
        tenure_days = (datetime.datetime.now(datetime.timezone.utc) - joined_at.replace(tzinfo=datetime.timezone.utc)).days if joined_at else 0
        efficiency = points / (tenure_days + 1) if tenure_days >= 0 else points
        
        # Activity Chart (Points & Voice last 7 days)
        chart_file = None
        chart_url = None
        daily_activity = self.db.get_user_daily_activity(main_id, interaction.guild_id, days=7)
        if daily_activity:
            os.makedirs("temp", exist_ok=True)
            path = f"temp/profile_{main_id}.png"
            draw_user_activity_chart(daily_activity, f"Activity: {user.display_name}", path)
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
        # This command shows your personal profile card with all your points
        target = interaction.user
        main_id = Config.get_main_id(target.id)
        main_member = interaction.guild.get_member(main_id) or target
        
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        try:
            view, chart_file = await self._prepare_profile(interaction, main_member, main_id)
            if not view:
                await interaction.followup.send(Messages.ERR_NO_DATA, ephemeral=True)
                return

            if chart_file:
                await interaction.followup.send(view=view, file=chart_file, ephemeral=True)
            else:
                await interaction.followup.send(view=view, ephemeral=True)
                
            # Step 2 cleanup: delete the file after sending (in a try/finally would be better but discord.py sends it async)
            # Actually discord.py File closes and we can delete it after the call.
            if chart_file and os.path.exists(chart_file.fp.name):
                try: os.remove(chart_file.fp.name)
                except: pass

        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(Messages.ERR_STATS_LOAD.format(e=e), ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        # This part listens for when someone clicks a button (like 'Weekly' or 'Share')
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("top:"):
                # Format: top:current_tf:action
                parts = custom_id.split(":")
                current_tf = parts[1] if len(parts) >= 2 else "alltime"
                action = parts[2] if len(parts) >= 3 else parts[1]
                
                timeframe = current_tf
                view = None
                chart_file = None

                if action in ["weekly", "monthly", "alltime"]:
                    timeframe = action
                    top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
                    view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
                elif action == "show_me":
                    main_id = Config.get_main_id(interaction.user.id)
                    main_member = interaction.guild.get_member(main_id) or interaction.user
                    view, chart_file = await self._prepare_profile(interaction, main_member, main_id)
                    if not view:
                        await interaction.response.send_message(Messages.ERR_NO_DATA_PERIOD, ephemeral=True)
                        return
                elif action == "share":
                    # Determine what to share
                    if current_tf == "me":
                        main_id = Config.get_main_id(interaction.user.id)
                        main_member = interaction.guild.get_member(main_id) or interaction.user
                        view_shared, chart_file = await self._prepare_profile(interaction, main_member, main_id, static=True, shared_by=interaction.user.display_name)
                    else:
                        top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, current_tf)
                        view_shared = ModernLeaderboardView(top_10, current_tf, interaction.guild, u_stats, static=True, shared_by=interaction.user.display_name)
                        chart_file = None

                    if chart_file:
                        await interaction.channel.send(view=view_shared, file=chart_file)
                        # Cleanup for share
                        if os.path.exists(chart_file.fp.name):
                            try: os.remove(chart_file.fp.name)
                            except: pass
                    else:
                        await interaction.channel.send(view=view_shared)
                    await interaction.response.send_message(Messages.SUCCESS_SHARED, ephemeral=True)
                    return
                
                if view:
                    # Note: Editing a message to add an attachment (chart_file) is complex via interaction.edit_message.
                    # For simple timeframe switching (LB), there's no chart, so it's fine.
                    # For show_me, we might want to just send a NEW message instead of editing if there's a chart,
                    # or keep show_me without chart in edit to avoid errors?
                    # Let's try sending a new one for show_me to keep it high quality.
                    if action == "show_me":
                        if chart_file:
                            await interaction.response.send_message(view=view, file=chart_file, ephemeral=True)
                        else:
                            await interaction.response.send_message(view=view, ephemeral=True)
                    else:
                        await interaction.response.edit_message(view=view)
                    
                    # Cleanup for show_me
                    if chart_file and os.path.exists(chart_file.fp.name):
                        try: os.remove(chart_file.fp.name)
                        except: pass
    
    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            # Tell the user how much longer they need to wait
            await interaction.response.send_message(
                Messages.ERR_COOLDOWN.format(retry_after=error.retry_after), 
                ephemeral=True
            )
        else:
            # For other errors, we can log them or let the global handler handle it
            raise error

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
