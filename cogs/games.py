import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages

class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.tracker = bot.tracker

    @app_commands.command(name="add_game", description=Messages.CMD_ADD_GAME_DESC)
    @app_commands.describe(search_name=Messages.CMD_ADD_GAME_NAME_DESC, role_suffix=Messages.CMD_ADD_GAME_SUFFIX_DESC)
    @app_commands.checks.has_permissions(administrator=True)
    async def add_game(self, interaction: discord.Interaction, search_name: str, role_suffix: str):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        self.db.add_tracked_game(search_name, role_suffix)
        await self.tracker.load_franchises()
        await interaction.response.send_message(Messages.GAME_ADDED.format(name=search_name, suffix=role_suffix), ephemeral=True)

    @app_commands.command(name="remove_game", description=Messages.CMD_REMOVE_GAME_DESC)
    @app_commands.describe(search_name=Messages.CMD_REMOVE_GAME_NAME_DESC)
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_game(self, interaction: discord.Interaction, search_name: str):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        self.db.remove_tracked_game(search_name)
        await self.tracker.load_franchises()
        await interaction.response.send_message(Messages.GAME_REMOVED.format(name=search_name), ephemeral=True)

    @app_commands.command(name="list_games", description=Messages.CMD_LIST_GAMES_DESC)
    @app_commands.checks.has_permissions(administrator=True)
    async def list_games(self, interaction: discord.Interaction):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        games = self.db.get_tracked_games()
        if not games:
            await interaction.response.send_message(Messages.GAME_LIST_EMPTY, ephemeral=True)
            return
        
        desc = "\n".join([f"• `{sub}` ➔ `Player: {suf}`" for sub, suf in self.tracker.franchises.items()])
        embed = discord.Embed(title=Messages.GAME_LIST_TITLE, description=desc, color=Config.COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="game_stats_report", description=Messages.CMD_GAME_REPORT_DESC)
    @app_commands.describe(timeframe=Messages.CMD_GAME_REPORT_TF_DESC)
    @app_commands.checks.has_permissions(administrator=True)
    async def game_stats_report(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return
            
        await interaction.response.send_message(Messages.GAME_REPORT_GEN, ephemeral=True)
        stats = self.db.get_game_stats_report(interaction.guild_id, timeframe)
        if not stats:
            await interaction.followup.send(Messages.GAME_REPORT_EMPTY, ephemeral=True)
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        title = Messages.GAME_POP_MONTHLY if timeframe == "monthly" else Messages.GAME_POP_ALLTIME
        lines = [Messages.GAME_POP_TITLE.format(tf=title), Messages.GAME_POP_GEN.format(now=now), ""]
        lines.append(Messages.GAME_POP_HEADER)
        lines.append("-" * 60)

        for display_name, user_count, total_mins in stats:
            lines.append(f"{display_name[:35]:<35} | {user_count:<5} | {int(total_mins or 0):<10}")
        
        filename = f"game_stats_{timeframe}_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        
        await interaction.followup.send(
            content=Messages.GAME_REPORT_DONE.format(tf=timeframe, count=len(stats)),
            file=discord.File(filename), 
            ephemeral=True
        )
        os.remove(filename)

async def setup(bot):
    await bot.add_cog(GamesCog(bot))
