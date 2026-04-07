import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from core.logger import log
from config_loader import Config
from core.messages import Messages
from core.ui_icons import Icons
from core.views import ModernElitesView
from core.ui_utils import get_feedback
from cogs.admin import is_admin_slash, is_tester_slash

class ElitesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.weekly_elites_task.start()

    def cog_unload(self):
        self.weekly_elites_task.cancel()

    async def _setup_roles(self, guild):
        """This little function checks if we have all our elite roles. If some are missing, it creates them for us!"""
        role_configs = Config.ELITE_ROLES
        
        updated = False
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        if "roles" not in config_data:
            config_data["roles"] = {}

        if "elite_roles" not in config_data:
            config_data["elite_roles"] = {}

        for key, data in role_configs.items():
            if key in ["title", "footer"]: continue
            name = data.get("name", key)
            color_str = data.get("color", "0xFFFFFF")
            try:
                color_int = int(str(color_str), 16)
            except:
                color_int = 0xFFFFFF

            role_id = data.get("role_id", 0)
            role = guild.get_role(role_id) if role_id else None
            
            if role:
                if role.name != name or role.color.value != color_int:
                    try:
                        await role.edit(name=name, color=discord.Color(color_int), reason="Syncing elite role with config.json")
                        log.info(f"Synchronized role: {name} (ID: {role.id})")
                    except discord.Forbidden:
                        log.warning(f"Forbidden: Could not update role {name}. Check bot permissions.")
            else:
                role = discord.utils.get(guild.roles, name=name)
                
                if not role:
                    try:
                        role = await guild.create_role(name=name, color=discord.Color(color_int), reason="Automated Elite System Setup")
                        log.info(f"Created role: {name}")
                    except discord.Forbidden:
                        log.error(f"Failed to create role {name}: Missing permissions.")
                        continue
                
                config_data["elite_roles"][key]["role_id"] = role.id
                updated = True
        
        if updated:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
            log.info("Updated config.json with new role IDs.")
            Config.reload()

    @tasks.loop(minutes=30)
    async def weekly_elites_task(self):
        """Every Monday morning, this function wakes up and checks who our weekly elites are!"""
        for guild in self.bot.guilds:
            if guild.id == Config.GUILD_ID:
                await self._run_elite_logic(guild)

    async def _run_elite_logic(self, guild, force=False):
        """This is where the magic happens! We calculate the winners and give out the shiny roles."""
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        
        if not force:
            if now.weekday() != 0: # Monday is 0
                return
                
            last_run = self.db.get_last_elites_run_date(guild.id)
            if last_run == today:
                return

        log.info(f"Starting Weekly Elite calculation (Force={force})...")
        
        await self._setup_roles(guild)
        
        start_date = today - datetime.timedelta(days=7)
        end_date = today - datetime.timedelta(days=1)
        
        stats = self.db.get_weekly_elite_stats(guild.id, start_date, end_date)
        
        categories = {}
        category_config_map = {
            "spotify": "spotify",
            "gamer_total": "godgamer",
            "gamer_variety": "godgamer",
            "streamer": "streamer",
            "media": "media"
        }
        
        for cat_id, cfg_key in category_config_map.items():
            candidates = stats.get(cat_id, [])
            stat_val = self._get_eligible_elite(guild, candidates)
            
            cfg = Config.ELITE_ROLES.get(cfg_key, {})
            role_id = cfg.get("role_id", 0)
            
            msg_template = {
                "spotify": Messages.ELITE_SPOTIFY,
                "gamer_total": Messages.ELITE_GAMER_TOTAL,
                "gamer_variety": Messages.ELITE_GAMER_VARIETY,
                "streamer": Messages.ELITE_STREAMER,
                "media": Messages.ELITE_MEMELORD
            }.get(cat_id, f"**{cfg.get('name', cat_id)}:** {{name}} ({{value}})")
            
            categories[cat_id] = (stat_val, role_id, msg_template)
        
        last_elites = self.db.get_last_elites(guild.id)
        roles_to_remove = set()
        
        for category, user_id in last_elites.items():
            member = guild.get_member(user_id)
            if member:
                cfg_key = category_config_map.get(category)
                role_id = Config.ELITE_ROLES.get(cfg_key, {}).get("role_id", 0)
                if role_id:
                    roles_to_remove.add((member, role_id))
        
        for m, rid in roles_to_remove:
            role = guild.get_role(rid)
            if role and role in m.roles:
                try: await m.remove_roles(role)
                except discord.Forbidden: pass
        
        elite_announcement_data = {}
        hof_notices = []
        
        for cat_id, (data, role_id, msg_template) in categories.items():
            if not data: continue
            
            uid, val = data
            member = guild.get_member(uid)
            
            self.db.log_elite_win(uid, guild.id, cat_id, today)
            
            role = guild.get_role(role_id)
            if member and role:
                try: await member.add_roles(role)
                except discord.Forbidden: pass
            
            elite_announcement_data[cat_id] = (uid, val, msg_template)
            
            wins = self.db.get_elite_wins(uid, guild.id)
            total_wins = sum(wins.values())
            if total_wins >= Config.ELITE_WIN_THRESHOLD:
                hof_role_id = Config.ELITE_ROLES.get("hall_of_fame", {}).get("role_id", 0)
                hof_role = guild.get_role(hof_role_id)
                if member and hof_role and hof_role not in member.roles:
                    try:
                        await member.add_roles(hof_role)
                        hof_notices.append(Messages.ELITE_HALL_OF_FAME.format(name=f"**{member.display_name}**"))
                    except discord.Forbidden: pass

        stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
        if stats_channel:
            view = ModernElitesView(guild, elite_announcement_data, hof_notices=hof_notices)
            await stats_channel.send(view=view)
            log.info(f"Weekly Elites announced in {stats_channel.name} using Modern UI")

    @discord.app_commands.command(name="elite-force", description=Messages.CMD_ELITES_FORCE_DESC)
    @is_admin_slash()
    async def force_calculate_elites(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            guild = interaction.guild
            if guild.id != Config.GUILD_ID:
                await interaction.followup.send(get_feedback('ERR_WRONG_GUILD', guild_id=Config.GUILD_ID), ephemeral=True)
                return
                
            await self._run_elite_logic(guild, force=True)
            await interaction.followup.send(get_feedback('SUCCESS_ELITES_FORCED'), ephemeral=True)
        except Exception as e:
            log.error(f"Error in force_calculate_elites: {e}")
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e), ephemeral=True)

    def _get_eligible_elite(self, guild, candidates):
        if not candidates:
            return None
            
        exclude_role_id = Config.ELITE_EXCLUDE_ROLE_ID
        
        for uid, val in candidates:
            member = guild.get_member(uid)
            if not member:
                continue
                
            if exclude_role_id != 0:
                if discord.utils.get(member.roles, id=exclude_role_id):
                    continue
            
            return (uid, val)
            
        return None

    @discord.app_commands.command(name="elite-log", description=Messages.CMD_ELITE_LOG_DESC)
    async def elite_log(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, category, COUNT(*) as wins FROM elite_history 
                WHERE guild_id = ? GROUP BY user_id, category ORDER BY wins DESC
            """, (interaction.guild_id,))
            rows = cursor.fetchall()
        
        if not rows:
            await interaction.followup.send(Messages.REPORT_ELITES_EMPTY, ephemeral=True)
            return

        user_wins = {}
        for uid, cat, count in rows:
            if uid not in user_wins: user_wins[uid] = {}
            user_wins[uid][cat] = count
        
        embed = discord.Embed(title=f"{Icons.ELITE_LOG} {Messages.REPORT_ELITES_TITLE}", color=0xFFD700)
        
        count = 0
        for uid, categories in user_wins.items():
            if count >= 10: break
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"Ismeretlen ({uid})"
            
            summary = []
            for cat, wins in categories.items():
                cat_name = {
                    "spotify": f"{Icons.SPOTIFY} {Messages.CAT_SPOTIFY}",
                    "gamer_total": f"{Icons.GAMER} {Messages.CAT_GAMER_TOTAL}",
                    "gamer_variety": f"{Icons.VARIETY} {Messages.CAT_GAMER_VARIETY}",
                    "streamer": f"{Icons.STREAMER} {Messages.CAT_STREAMER}",
                    "media": f"{Icons.MEME} {Messages.CAT_MEME}"
                }.get(cat, cat)
                summary.append(f"{cat_name}: {wins}x")
            
            embed.add_field(name=name, value=" | ".join(summary), inline=False)
            count += 1
            
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="test-weekly-layout", description=Messages.CMD_TEST_WEEKLY_LAYOUT_DESC)
    @is_admin_slash()
    async def test_weekly_layout(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        uid = interaction.user.id
        dummy_data = {
            "spotify": (uid, 120, Messages.ELITE_SPOTIFY),
            "gamer_total": (uid, 450, Messages.ELITE_GAMER_TOTAL),
            "gamer_variety": (uid, 5, Messages.ELITE_GAMER_VARIETY),
            "streamer": (uid, 60, Messages.ELITE_STREAMER),
            "media": (uid, 25, Messages.ELITE_MEMELORD)
        }
        dummy_hof = [Messages.ELITE_HALL_OF_FAME.format(name=f"**{interaction.user.display_name}**")]
        
        try:
            view = ModernElitesView(interaction.guild, dummy_data, hof_notices=dummy_hof)
            await interaction.followup.send(view=view, ephemeral=True)
        except Exception as e:
            log.error(f"Error in test_weekly_layout: {e}", exc_info=True)
            await interaction.followup.send(get_feedback('ERR_LAYOUT_TEST', e=e), ephemeral=True)

    @discord.app_commands.command(name="weekly-chances", description=Messages.CMD_WEEKLY_STANDINGS_DESC)
    async def weekly_chances(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        start_date = (now - datetime.timedelta(days=now.weekday())).date()
        today = now.date()
        
        stats = self.db.get_weekly_elite_stats(interaction.guild_id, start_date, today)
        caller_stats = self.db.get_user_weekly_elite_stats(interaction.user.id, interaction.guild_id, start_date, today)
        
        categories = {}
        category_config_map = {
            "spotify": "spotify",
            "gamer_total": "godgamer",
            "gamer_variety": "godgamer",
            "streamer": "streamer",
            "media": "media"
        }
        
        for cat_id, cfg_key in category_config_map.items():
            candidates = stats.get(cat_id, [])
            stat_val = self._get_eligible_elite(interaction.guild, candidates)
            
            cfg = Config.ELITE_ROLES.get(cfg_key, {})
            
            msg_template = {
                "spotify": Messages.ELITE_SPOTIFY,
                "gamer_total": Messages.ELITE_GAMER_TOTAL,
                "gamer_variety": Messages.ELITE_GAMER_VARIETY,
                "streamer": Messages.ELITE_STREAMER,
                "media": Messages.ELITE_MEMELORD
            }.get(cat_id, f"**{cfg.get('name', cat_id)}:** {{name}} ({{value}})")
            
            categories[cat_id] = (stat_val, msg_template)
        
        elite_data = {}
        for cat_id, (data, msg_template) in categories.items():
            if not data: continue
            uid, val = data
            elite_data[cat_id] = (uid, val, msg_template)
            
        try:
            view = ModernElitesView(
                interaction.guild, 
                elite_data, 
                title=Messages.WEEKLY_STANDINGS_TITLE,
                footer=Messages.WEEKLY_STANDINGS_FOOTER,
                caller_id=interaction.user.id,
                caller_stats=caller_stats
            )
            await interaction.followup.send(view=view)
        except Exception as e:
            log.error(f"Error in weekly_chances: {e}")
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e), ephemeral=True)

async def setup(bot):
    await bot.add_cog(ElitesCog(bot))
