import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from core.logger import log
from config_loader import Config
from core.messages import Messages
from core.ui_icons import Icons
from core.views import ModernChampionsView
from core.ui_utils import get_feedback
from cogs.admin import is_admin_slash, is_tester_slash

class ChampionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.weekly_champions_task.start()

    def cog_unload(self):
        self.weekly_champions_task.cancel()

    async def _setup_roles(self, guild):
        """Automatically creates the champion roles if they are missing and updates the config."""
        role_configs = Config.CHAMPION_ROLES
        
        updated = False
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        if "roles" not in config_data:
            config_data["roles"] = {}

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
                # Sync existing role if name or color changed in config
                if role.name != name or role.color.value != color_int:
                    try:
                        await role.edit(name=name, color=discord.Color(color_int), reason="Syncing champion role with config.json")
                        log.info(f"Synchronized role: {name} (ID: {role.id})")
                    except discord.Forbidden:
                        log.warning(f"Forbidden: Could not update role {name}. Check bot permissions.")
            else:
                # Try to find by name if ID is missing or invalid
                role = discord.utils.get(guild.roles, name=name)
                
                if not role:
                    try:
                        role = await guild.create_role(name=name, color=discord.Color(color_int), reason="Automated Champion System Setup")
                        log.info(f"Created role: {name}")
                    except discord.Forbidden:
                        log.error(f"Failed to create role {name}: Missing permissions.")
                        continue
                
                config_data["champion_roles"][key]["role_id"] = role.id
                updated = True
        
        if updated:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
            log.info("Updated config.json with new role IDs.")
            Config.reload()

    @tasks.loop(minutes=30)
    async def weekly_champions_task(self):
        """Runs the champion logic every Monday at 00:01 (handled by _run_champion_logic checks)."""
        for guild in self.bot.guilds:
            if guild.id == Config.GUILD_ID:
                await self._run_champion_logic(guild)

    async def _run_champion_logic(self, guild, force=False):
        """Internal logic for calculating and awarding weekly champions."""
        now = datetime.datetime.now(datetime.timezone.utc)
        today = now.date()
        
        # 1. Validation for automatic task (skip if not Monday or already run)
        if not force:
            if now.weekday() != 0: # Monday is 0
                return
                
            # Ensure we only run once per Monday
            with self.db._get_connection() as conn:
                row = conn.execute("SELECT MAX(win_date) FROM champion_history WHERE guild_id = ?", (guild.id,)).fetchone()
                last_run = datetime.date.fromisoformat(row[0]) if row and row[0] else None
            
            if last_run == today:
                return

        # Start the process!
        log.info(f"Starting Weekly Champion calculation (Force={force})...")
        
        await self._setup_roles(guild)
        
        # Period: Last Monday 00:00 to Sunday 23:59
        start_date = today - datetime.timedelta(days=7)
        end_date = today - datetime.timedelta(days=1)
        
        stats = self.db.get_weekly_champion_stats(guild.id, start_date, end_date)
        
        # Fetch winners (Map categories to consolidated config keys)
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
            stat_val = self._get_eligible_champion(guild, candidates)
            
            cfg = Config.CHAMPION_ROLES.get(cfg_key, {})
            role_id = cfg.get("role_id", 0)
            
            # Get template from Messages (localized)
            msg_template = {
                "spotify": Messages.CHAMPION_SPOTIFY,
                "gamer_total": Messages.CHAMPION_GAMER_TOTAL,
                "gamer_variety": Messages.CHAMPION_GAMER_VARIETY,
                "streamer": Messages.CHAMPION_STREAMER,
                "media": Messages.CHAMPION_MEMELORD
            }.get(cat_id, f"**{cfg.get('name', cat_id)}:** {{name}} ({{value}})")
            
            categories[cat_id] = (stat_val, role_id, msg_template)
        
        # Manage old roles (using a set to avoid removing/checking the same role multiple times)
        last_champs = self.db.get_last_champions(guild.id)
        roles_to_remove = set()
        
        for category, user_id in last_champs.items():
            member = guild.get_member(user_id)
            if member:
                cfg_key = category_config_map.get(category)
                role_id = Config.CHAMPION_ROLES.get(cfg_key, {}).get("role_id", 0)
                if role_id:
                    roles_to_remove.add((member, role_id))
        
        for m, rid in roles_to_remove:
            role = guild.get_role(rid)
            if role and role in m.roles:
                try: await m.remove_roles(role)
                except discord.Forbidden: pass
        
        # Award new ones & collect data for the view
        champion_announcement_data = {}
        hof_notices = []
        
        for cat_id, (data, role_id, msg_template) in categories.items():
            if not data: continue
            
            uid, val = data
            member = guild.get_member(uid)
            
            # 1. Log win
            self.db.log_champion_win(uid, guild.id, cat_id, today)
            
            # 2. Add role
            role = guild.get_role(role_id)
            if member and role:
                try: await member.add_roles(role)
                except discord.Forbidden: pass
            
            # 3. Collect for view (using name/mention as appropriate in view)
            champion_announcement_data[cat_id] = (uid, val, msg_template)
            
            # 4. Check Hall of Fame
            wins = self.db.get_champion_wins(uid, guild.id)
            total_wins = sum(wins.values())
            if total_wins >= Config.CHAMPION_WIN_THRESHOLD:
                hof_role_id = Config.CHAMPION_ROLES.get("hall_of_fame", {}).get("role_id", 0)
                hof_role = guild.get_role(hof_role_id)
                if member and hof_role and hof_role not in member.roles:
                    try:
                        await member.add_roles(hof_role)
                        # Use localized Hall of Fame message
                        hof_notices.append(Messages.CHAMPION_HALL_OF_FAME.format(name=f"**{member.display_name}**"))
                    except discord.Forbidden: pass

        # Send to stats channel using ModernChampionsView
        stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
        if stats_channel:
            view = ModernChampionsView(guild, champion_announcement_data, hof_notices=hof_notices)
            
            # The view now handles HOF integration in a premium layout
            await stats_channel.send(view=view)
            
            log.info(f"Weekly Champions announced in {stats_channel.name} using Modern UI")

    @discord.app_commands.command(name="champ-force", description=Messages.CMD_CHAMPIONS_FORCE_DESC)
    @is_admin_slash()
    async def force_calculate_champions(self, interaction: discord.Interaction):
        """Forces the weekly champion calculation logic immediately."""
        await interaction.response.defer(ephemeral=True)
        try:
            guild = interaction.guild
            if guild.id != Config.GUILD_ID:
                await interaction.followup.send(get_feedback('ERR_WRONG_GUILD', guild_id=Config.GUILD_ID), ephemeral=True)
                return
                
            await self._run_champion_logic(guild, force=True)
            await interaction.followup.send(get_feedback('SUCCESS_CHAMPIONS_FORCED'), ephemeral=True)
        except Exception as e:
            log.error(f"Error in force_calculate_champions: {e}")
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e), ephemeral=True)


    def _get_eligible_champion(self, guild, candidates):
        """Processes a list of candidates and returns the first one that doesn't have the exclude role."""
        if not candidates:
            return None
            
        exclude_role_id = Config.CHAMPION_EXCLUDE_ROLE_ID
        
        for uid, val in candidates:
            member = guild.get_member(uid)
            if not member:
                continue
                
            # If exclusion role is set, check if user has it
            if exclude_role_id != 0:
                if discord.utils.get(member.roles, id=exclude_role_id):
                    continue
            
            # Found the top eligible candidate!
            return (uid, val)
            
        return None

    @discord.app_commands.command(name="champion-log", description=Messages.CMD_CHAMPION_LOG_DESC)
    async def champion_log(self, interaction: discord.Interaction):
        # Usable everywhere
        await interaction.response.defer(ephemeral=True)
        
        # Get overall stats from DB
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, category, COUNT(*) as wins FROM champion_history 
                WHERE guild_id = ? GROUP BY user_id, category ORDER BY wins DESC
            """, (interaction.guild_id,))
            rows = cursor.fetchall()
        
        if not rows:
            await interaction.followup.send(Messages.REPORT_CHAMPIONS_EMPTY, ephemeral=True)
            return

        # Group by user
        user_wins = {}
        for uid, cat, count in rows:
            if uid not in user_wins: user_wins[uid] = {}
            user_wins[uid][cat] = count
        
        embed = discord.Embed(title=f"{Icons.CHAMPION_LOG} {Messages.REPORT_CHAMPIONS_TITLE}", color=0xFFD700)
        
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
        """A test command to preview the new layout with dummy data."""
        await interaction.response.defer(ephemeral=True)
        # Dummy data for the preview
        uid = interaction.user.id
        dummy_data = {
            "spotify": (uid, 120, Messages.CHAMPION_SPOTIFY),
            "gamer_total": (uid, 450, Messages.CHAMPION_GAMER_TOTAL),
            "gamer_variety": (uid, 5, Messages.CHAMPION_GAMER_VARIETY),
            "streamer": (uid, 60, Messages.CHAMPION_STREAMER),
            "media": (uid, 25, Messages.CHAMPION_MEMELORD)
        }
        # Define HOF with bold name instead of mention
        dummy_hof = [Messages.CHAMPION_HALL_OF_FAME.format(name=f"**{interaction.user.display_name}**")]
        
        try:
            view = ModernChampionsView(interaction.guild, dummy_data, hof_notices=dummy_hof)
            
            # Since Components V2 doesn't allow 'content' alongside 'view', 
            # we would normally add a TextDisplay to the view, but for a simple test,
            # we'll just send the view alone. 
            await interaction.followup.send(
                view=view, 
                ephemeral=True
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            await interaction.followup.send(get_feedback('ERR_LAYOUT_TEST', e=e), ephemeral=True)

    @discord.app_commands.command(name="weekly-chances", description=Messages.CMD_WEEKLY_STANDINGS_DESC)
    async def weekly_chances(self, interaction: discord.Interaction):
        """Shows current standings and compares them with the user's data."""
        await interaction.response.defer(ephemeral=True)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        # This Monday 00:00
        start_date = (now - datetime.timedelta(days=now.weekday())).date()
        today = now.date()
        
        # 1. Guild leader stats
        stats = self.db.get_weekly_champion_stats(interaction.guild_id, start_date, today)
        
        # 2. Caller's stats
        caller_stats = self.db.get_user_weekly_champion_stats(interaction.user.id, interaction.guild_id, start_date, today)
        
        # Map categories to roles/messages (Map categories to consolidated config keys)
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
            stat_val = self._get_eligible_champion(interaction.guild, candidates)
            
            cfg = Config.CHAMPION_ROLES.get(cfg_key, {})
            
            msg_template = {
                "spotify": Messages.CHAMPION_SPOTIFY,
                "gamer_total": Messages.CHAMPION_GAMER_TOTAL,
                "gamer_variety": Messages.CHAMPION_GAMER_VARIETY,
                "streamer": Messages.CHAMPION_STREAMER,
                "media": Messages.CHAMPION_MEMELORD
            }.get(cat_id, f"**{cfg.get('name', cat_id)}:** {{name}} ({{value}})")
            
            categories[cat_id] = (stat_val, msg_template)
        
        champion_data = {}
        for cat_id, (data, msg_template) in categories.items():
            if not data: continue
            uid, val = data
            champion_data[cat_id] = (uid, val, msg_template)
            
        try:
            view = ModernChampionsView(
                interaction.guild, 
                champion_data, 
                title=Messages.WEEKLY_STANDINGS_TITLE,
                footer=Messages.WEEKLY_STANDINGS_FOOTER,
                caller_id=interaction.user.id,
                caller_stats=caller_stats
            )
            
            await interaction.followup.send(view=view)
        except Exception as e:
            log.error(f"Error in heti_eselyek: {e}")
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e), ephemeral=True)

async def setup(bot):
    await bot.add_cog(ChampionsCog(bot))
