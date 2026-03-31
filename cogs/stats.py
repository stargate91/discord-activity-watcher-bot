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
    async def top(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        # This command shows the Top 10 leaderboard (highest scores) for the server
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID), ephemeral=True)
            return

        top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
        view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
        await interaction.response.send_message(view=view, ephemeral=True)

    @app_commands.command(name="me", description=Messages.CMD_ME_MEMBER_DESC)
    async def me(self, interaction: discord.Interaction):
        # This command shows your personal profile card with all your points
        target = interaction.user
        main_id = Config.get_main_id(target.id)
        
        # If the user is an 'alt' account, we show the main account's stats instead
        main_member = interaction.guild.get_member(main_id) or target
        
        if Config.STATS_CHANNEL_ID != 0 and interaction.channel_id != Config.STATS_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_STATS_CHANNEL.format(id=Config.STATS_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        try:
            # Use the main_id for stat retrieval
            _, user_full_stats = self.bot.engine.get_leaderboard(
                interaction.guild, 
                user=main_member, 
                live_voice_times=self.bot.voice_start_times
            )
            
            if not user_full_stats:
                await interaction.followup.send(Messages.ERR_NO_DATA, ephemeral=True)
                return

            # user_full_stats contains (user, data, points, voice_mins, rank)
            user, data, points, voice_mins, rank = user_full_stats
            
            # Calculate extra social stats (who they talk to most, favorite emoji, etc.)
            social = self.db.get_user_social_stats(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
            partners = self.db.get_top_voice_partners(user.id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
            top_games = self.db.get_user_top_games(user.id, interaction.guild_id, limit=3)
            
            # Calculate Daily Average (30 days)
            monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
            user_monthly = monthly_data.get(user.id, {"messages":0})
            avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
            
            # Avg Voice Session Duration
            avg_voice = self.db.get_user_average_voice_duration(user.id, interaction.guild_id)
            
            view = ModernProfileView(user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice)
            await interaction.followup.send(view=view, ephemeral=True)
        except Exception as e:
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

                if action in ["weekly", "monthly", "alltime"]:
                    timeframe = action
                    top_10, u_stats = self.bot.get_top_data(interaction.guild, interaction.user, timeframe)
                    view = ModernLeaderboardView(top_10, timeframe, interaction.guild, u_stats)
                elif action == "show_me":
                    main_id = Config.get_main_id(interaction.user.id)
                    main_member = interaction.guild.get_member(main_id) or interaction.user
                    
                    top_10, u_stats = self.bot.get_top_data(interaction.guild, main_member, timeframe)
                    if not u_stats:
                        await interaction.response.send_message(Messages.ERR_NO_DATA_PERIOD, ephemeral=True)
                        return
                    
                    user, data, points, voice_mins, rank = u_stats
                    social = self.db.get_user_social_stats(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    partners = self.db.get_top_voice_partners(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    top_games = self.db.get_user_top_games(main_id, interaction.guild_id, limit=3)
                    
                    monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                    user_monthly = monthly_data.get(main_id, {"messages":0})
                    avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
                    avg_voice = self.db.get_user_average_voice_duration(main_id, interaction.guild_id)
                    
                    view = ModernProfileView(main_member, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, timeframe="me")
                elif action == "share":
                    # Determine what to share
                    if current_tf == "me":
                        # We must use the Main ID to get the combined stats for sharing
                        main_id = Config.get_main_id(interaction.user.id)
                        main_member = interaction.guild.get_member(main_id) or interaction.user
                        
                        _, u_stats = self.bot.get_top_data(interaction.guild, main_member, "alltime")
                        if not u_stats: return
                        user, data, points, voice_mins, rank = u_stats
                        
                        social = self.db.get_user_social_stats(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        partners = self.db.get_top_voice_partners(main_id, interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        top_games = self.db.get_user_top_games(main_id, interaction.guild_id, limit=3)
                        
                        monthly_data = self.db.get_leaderboard_data(interaction.guild_id, days=Config.SOCIAL_STATS_DAYS)
                        user_monthly = monthly_data.get(main_id, {"messages":0})
                        avg_daily = user_monthly["messages"] / Config.SOCIAL_STATS_DAYS
                        avg_voice = self.db.get_user_average_voice_duration(main_id, interaction.guild_id)
                        
                        view_shared = ModernProfileView(main_member, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, static=True, shared_by=interaction.user.display_name)
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
