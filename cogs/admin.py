import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages
from core.views import ModernInfoView

def is_admin():
    # This is a custom check to see if someone can use admin prefix commands
    async def predicate(ctx):
        # 1. Server Administrators can always use them
        if ctx.author.guild_permissions.administrator:
            return True
        # 2. People with the special Admin Role ID can also use them
        if Config.ADMIN_ROLE_ID != 0 and discord.utils.get(ctx.author.roles, id=Config.ADMIN_ROLE_ID):
            return True
        return False
    return commands.check(predicate)

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

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
            d = guild_data.get(m.id)
            if not d: continue
            
            voice_mins = d['voice_minutes']
            if m.id in self.bot.voice_start_times:
                voice_mins += (now - self.bot.voice_start_times[m.id]).total_seconds() / 60
                
            s = Messages.REPORT_STAGE_NORMAL
            if r1 in m.roles: s = Messages.REPORT_STAGE_1
            elif r2 in m.roles: s = Messages.REPORT_STAGE_2
            det = Messages.REPORT_INACTIVE if s == Messages.REPORT_STAGE_1 else (Messages.REPORT_S2_RETURN.format(days=7-(now-d['returned_at'].astimezone(datetime.timezone.utc)).days) if s == Messages.REPORT_STAGE_2 and d["returned_at"] else Messages.REPORT_S1_LIMIT.format(days=Config.STAGE_1_DAYS-(now-d['last_active'].astimezone(datetime.timezone.utc)).days))
            lines.append(f"{str(m)[:25]:<25} | {s:<12} | {d['message_count']:<4} | {d['reaction_count']:<4} | {int(voice_mins):<4} | {det}")
        
        # Save everything into a .txt file and send it to the admin
        filename = f"report_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        # Delete the file from the computer after sending it
        os.remove(filename)

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
    @app_commands.checks.has_permissions(administrator=True)
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

    @commands.command()
    @commands.guild_only()
    @is_admin()
    async def sync(self, ctx: commands.Context, spec: str | None = None):
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

    @commands.command(name="clear_commands")
    @commands.guild_only()
    @is_admin()
    async def clear_commands_prefix(self, ctx: commands.Context):
        # This part removes all the slash commands from Discord for this bot
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
        
        await ctx.send(Messages.CMD_CLEAR_DONE)

    @app_commands.command(name="sync", description=Messages.CMD_SYNC_DESC)
    @app_commands.describe(mode=Messages.CMD_SYNC_MODE_DESC)
    @app_commands.checks.has_permissions(administrator=True)
    async def sync_slash(self, interaction: discord.Interaction, mode: str = "guild"):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        if not await self.bot.is_owner(interaction.user):
            await interaction.response.send_message(Messages.ERR_OWNER_ONLY, ephemeral=True)
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

    @commands.command(name="info")
    @is_admin()
    async def info_prefix(self, ctx: commands.Context):
        # This command posts the bot's introduction card to the stats channel
        stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
        if not stats_channel:
            await ctx.send(Messages.ERR_STATS_NOT_FOUND)
            return
            
        view = ModernInfoView(ctx.guild)
        await stats_channel.send(view=view)
        await ctx.send(Messages.INFO_POSTED.format(channel=stats_channel.mention))

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
