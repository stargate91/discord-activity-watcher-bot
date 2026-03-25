import discord
from discord.ext import commands
from discord import app_commands
import datetime
from config_loader import Config
from core.messages import Messages
from core.views import ModernLeaderboardView, ModernProfileView

class StatsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.engine = bot.engine

    @app_commands.command(name="top", description="Mutatja a heti, havi vagy összesített toplistát.")
    @app_commands.describe(timeframe="Válassz időszakot (weekly, monthly, alltime)")
    async def top(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
        view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="me", description="Megmutatja a saját aktivitási statisztikáidat.")
    async def me(self, interaction: discord.Interaction):
        # Use centralized logic for points and rank
        _, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, "alltime")
        
        if not u_stats:
            await interaction.response.send_message(Messages.ERR_NO_DATA, ephemeral=True)
            return

        # u_stats: (user, db_data, points, voice_mins, rank)
        user, data, points, voice_mins, rank = u_stats
        
        # Advanced calculations
        social = self.db.get_user_social_stats(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        partners = self.db.get_top_voice_partners(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        recent_games = self.db.get_user_recent_games(user.id, interaction.guild_id, limit=Config.RECENT_GAMES_LIMIT)
        
        # Calculate Daily Average (30 days)
        monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
        user_monthly = monthly_data.get(user.id, {"messages":0})
        avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
        
        view = ModernProfileView(user, data, points, voice_mins, social, partners, rank, recent_games, avg_daily)
        await interaction.response.send_message(view=view, ephemeral=True)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("top:"):
                # Format: top:current_tf:action
                parts = custom_id.split(":")
                current_tf = parts[1] if len(parts) >= 2 else "alltime"
                action = parts[2] if len(parts) >= 3 else parts[1]
                
                timeframe = current_tf
                view = None

                if action in ["weekly", "monthly", "alltime"]:
                    timeframe = action
                    top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
                    view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
                elif action == "show_me":
                    top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
                    if not u_stats:
                        await interaction.response.send_message(Messages.ERR_NO_DATA_PERIOD, ephemeral=True)
                        return
                    
                    user, data, points, voice_mins, rank = u_stats
                    social = self.db.get_user_social_stats(interaction.user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    partners = self.db.get_top_voice_partners(interaction.user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    recent_games = self.db.get_user_recent_games(interaction.user.id, interaction.guild_id, limit=Config.RECENT_GAMES_LIMIT)
                    
                    monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    user_monthly = monthly_data.get(interaction.user.id, {"messages":0})
                    avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
                    
                    view = ModernProfileView(interaction.user, data, points, voice_mins, social, partners, rank, recent_games, avg_daily, timeframe="me")
                elif action == "share":
                    # Determine what to share
                    if current_tf == "me":
                        _, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, "alltime")
                        if not u_stats: return
                        user, data, points, voice_mins, rank = u_stats
                        
                        social = self.db.get_user_social_stats(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        partners = self.db.get_top_voice_partners(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        recent_games = self.db.get_user_recent_games(user.id, interaction.guild_id, limit=Config.RECENT_GAMES_LIMIT)
                        
                        monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        user_monthly = monthly_data.get(user.id, {"messages":0})
                        avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
                        
                        view_shared = ModernProfileView(user, data, points, voice_mins, social, partners, rank, recent_games, avg_daily, static=True, shared_by=interaction.user.display_name)
                    else:
                        top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, current_tf)
                        view_shared = ModernLeaderboardView(top_10, current_tf, interaction.guild, u_stats, static=True, shared_by=interaction.user.display_name)

                    await interaction.channel.send(view=view_shared)
                    await interaction.response.send_message(Messages.SUCCESS_SHARED, ephemeral=True)
                    return
                
                if view:
                    await interaction.response.edit_message(view=view)

async def setup(bot):
    await bot.add_cog(StatsCog(bot))
