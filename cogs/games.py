import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages
from cogs.admin import is_admin_slash, is_tester_slash




class GamesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.tracker = bot.tracker
        
        # We need to make sure the command descriptions look nice when the bot starts up
        for cmd in self.get_app_commands():
             if not hasattr(cmd, "_raw_desc"):
                 cmd._raw_desc = cmd.description
             cmd.description = Config.format_desc(cmd._raw_desc)

    def refresh_descriptions(self, guild):
        """This function updates the command descriptions with the actual names from your server!"""
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild)

    @app_commands.command(name="add-game", description=Messages.CMD_ADD_GAME_DESC)
    @app_commands.describe(search_name=Messages.CMD_ADD_GAME_NAME_DESC, role_suffix=Messages.CMD_ADD_GAME_SUFFIX_DESC)
    @is_admin_slash()
    async def add_game(self, interaction: discord.Interaction, search_name: str, role_suffix: str):
        # This command tells the bot to start watching a new game!
        self.db.add_tracked_game(search_name, role_suffix)
        await self.tracker.load_franchises()
        await interaction.response.send_message(Messages.GAME_ADDED.format(name=search_name, suffix=role_suffix), ephemeral=True)

    @app_commands.command(name="remove-game", description=Messages.CMD_REMOVE_GAME_DESC)
    @app_commands.describe(search_name=Messages.CMD_REMOVE_GAME_NAME_DESC)
    @is_admin_slash()
    async def remove_game(self, interaction: discord.Interaction, search_name: str):
        # This command tells the bot to stop watching a specific game
        self.db.remove_tracked_game(search_name)
        await self.tracker.load_franchises()
        await interaction.response.send_message(Messages.GAME_REMOVED.format(name=search_name), ephemeral=True)

    @remove_game.autocomplete("search_name")
    async def remove_game_autocomplete(self, interaction: discord.Interaction, current: str):
        games = self.db.get_tracked_games()
        return [
            app_commands.Choice(name=name, value=name)
            for name in games.keys() if current.lower() in name.lower()
        ][:25]

    @app_commands.command(name="list-games", description=Messages.CMD_LIST_GAMES_DESC)
    @is_tester_slash()
    async def list_games(self, interaction: discord.Interaction):
        # This command shows a list of every game the bot is currently keeping an eye on!
        games = self.db.get_tracked_games()
        if not games:
            await interaction.response.send_message(Messages.GAME_LIST_EMPTY, ephemeral=True)
            return
        
        desc = "\n".join([f"• `{sub}` ➔ `Player: {suf}`" for sub, suf in self.tracker.franchises.items()])
        embed = discord.Embed(title=Messages.GAME_LIST_TITLE, description=desc, color=Config.COLOR_SUCCESS)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="game-stats-report", description=Messages.CMD_GAME_REPORT_DESC)
    @app_commands.describe(timeframe=Messages.CMD_GAME_REPORT_TF_DESC)
    @is_tester_slash()
    async def game_stats_report(self, interaction: discord.Interaction, timeframe: str = "alltime"):
        # We're making a text file that shows which games are the most popular in the server!
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
