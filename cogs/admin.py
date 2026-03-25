import discord
from discord.ext import commands
from discord import app_commands
import datetime
import os
from config_loader import Config
from core.messages import Messages

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @app_commands.command(name="status_report", description="[Admin Channel] Generál egy részletes TXT jelentést.")
    async def status_report(self, interaction: discord.Interaction):
        if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
            await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.ADMIN_CHANNEL_ID), ephemeral=True)
            return

        await interaction.response.send_message(Messages.REPORT_GEN_STATUS, ephemeral=True)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        guild_data = self.db.get_all_guild_data(interaction.guild_id)
        r1, r2 = interaction.guild.get_role(Config.STAGE_1_ROLE_ID), interaction.guild.get_role(Config.STAGE_2_ROLE_ID)
        lines = [Messages.REPORT_TITLE_HEADER.format(guild=interaction.guild.name, now=now)]
        
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
        
        filename = f"report_{interaction.guild_id}.txt"
        with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
        await interaction.followup.send(file=discord.File(filename), ephemeral=True)
        os.remove(filename)

    @app_commands.command(name="game_role_report", description="[Admin Channel] Letölti a játékos-rang kiosztások naplóját.")
    async def game_role_report(self, interaction: discord.Interaction):
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

    @app_commands.command(name="reset_database", description="[Admin] MINDEN aktivitási adat végleges törlése.")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_database(self, interaction: discord.Interaction):
        try:
            self.db.reset_database()
            await interaction.response.send_message(Messages.DB_RESET_SUCCESS, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(Messages.DB_RESET_ERROR.format(e=e), ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
