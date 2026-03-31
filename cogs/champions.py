import discord
from discord.ext import commands, tasks
import datetime
import json
import os
from core.logger import log
from config_loader import Config
from core.messages import Messages

class ChampionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.weekly_champions_task.start()

    def cog_unload(self):
        self.weekly_champions_task.cancel()

    async def _setup_roles(self, guild):
        """Automatically creates the champion roles if they are missing and updates the config."""
        role_configs = [
            ("spotivibe_id", "SpotiVibe", 0x1DB954),
            ("godgamer_total_id", "GodGamer (Hardcore)", 0xFFD700),
            ("godgamer_variety_id", "GodGamer (Sokszínű)", 0xFFD700),
            ("sharing_id", "Sharing is Caring", 0x9146FF),
            ("hall_of_famer_id", "Hall of Famer", 0xB9F2FF)
        ]
        
        updated = False
        with open("config.json", "r", encoding="utf-8") as f:
            config_data = json.load(f)
        
        if "roles" not in config_data:
            config_data["roles"] = {}

        for key, name, color in role_configs:
            role_id = config_data["roles"].get(key, 0)
            role = guild.get_role(role_id) if role_id else None
            
            if not role:
                # Search by name first to avoid duplicates
                role = discord.utils.get(guild.roles, name=name)
                
                if not role:
                    try:
                        role = await guild.create_role(name=name, color=discord.Color(color), reason="Automated Champion System Setup")
                        log.info(f"Created role: {name}")
                    except discord.Forbidden:
                        log.error(f"Failed to create role {name}: Missing permissions.")
                        continue
                
                config_data["roles"][key] = role.id
                # Update Config class attributes dynamically
                setattr(Config, key.upper(), role.id)
                updated = True
        
        if updated:
            with open("config.json", "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=4)
            log.info("Updated config.json with new role IDs.")

    @tasks.loop(minutes=30)
    async def weekly_champions_task(self):
        """Runs the champion logic every Monday at 00:01."""
        now = datetime.datetime.now(datetime.timezone.utc)
        
        # We only care about Monday morning
        if now.weekday() != 0: # Monday is 0
            return
            
        # Ensure we only run once per Monday
        # We'll check the db for the last win_date
        with self.db._get_connection() as conn:
            row = conn.execute("SELECT MAX(win_date) FROM champion_history").fetchone()
            last_run = datetime.date.fromisoformat(row[0]) if row and row[0] else None
        
        today = now.date()
        if last_run == today:
            return

        # Start the process!
        log.info("Starting Weekly Champion calculation...")
        
        for guild in self.bot.guilds:
            if guild.id != Config.GUILD_ID: continue
            
            await self._setup_roles(guild)
            
            # Period: Last Monday 00:00 to Sunday 23:59
            start_date = today - datetime.timedelta(days=7)
            end_date = today - datetime.timedelta(days=1)
            
            stats = self.db.get_weekly_champion_stats(guild.id, start_date, end_date)
            
            # Fetch winners
            categories = {
                "spotify": (stats.get("spotify"), Config.SPOTIVIBE_ROLE_ID, Messages.CHAMPION_SPOTIFY),
                "gamer_total": (stats.get("gamer_total"), Config.GODGAMER_TOTAL_ROLE_ID, Messages.CHAMPION_GAMER_TOTAL),
                "gamer_variety": (stats.get("gamer_variety"), Config.GODGAMER_VARIETY_ROLE_ID, Messages.CHAMPION_GAMER_VARIETY),
                "streamer": (stats.get("streamer"), Config.SHARING_ROLE_ID, Messages.CHAMPION_STREAMER)
            }
            
            # Manage old roles
            last_champs = self.db.get_last_champions(guild.id)
            for category, user_id in last_champs.items():
                member = guild.get_member(user_id)
                if member:
                    # Map category to role ID
                    role_id = 0
                    if category == "spotify": role_id = Config.SPOTIVIBE_ROLE_ID
                    elif category == "gamer_total": role_id = Config.GODGAMER_TOTAL_ROLE_ID
                    elif category == "gamer_variety": role_id = Config.GODGAMER_VARIETY_ROLE_ID
                    elif category == "streamer": role_id = Config.SHARING_ROLE_ID
                    
                    role = guild.get_role(role_id)
                    if role and role in member.roles:
                        try: await member.remove_roles(role)
                        except discord.Forbidden: pass
            
            # Award new ones & build message
            announcement_lines = [Messages.CHAMPIONS_TITLE]
            hof_winners = []
            
            for cat_id, (data, role_id, msg_template) in categories.items():
                if not data: continue
                
                uid, val = data
                member = guild.get_member(uid)
                name = member.display_name if member else Messages.LB_UNKNOWN_USER.format(id=uid)
                
                # 1. Log win
                self.db.log_champion_win(uid, guild.id, cat_id, today)
                
                # 2. Add role
                role = guild.get_role(role_id)
                if member and role:
                    try: await member.add_roles(role)
                    except discord.Forbidden: pass
                
                # 3. Add to message
                announcement_lines.append(msg_template.format(name=name, value=val))
                
                # 4. Check Hall of Fame
                wins = self.db.get_champion_wins(uid, guild.id)
                total_wins = sum(wins.values())
                if total_wins >= Config.CHAMPION_WIN_THRESHOLD:
                    hof_role = guild.get_role(Config.HALL_OF_FAMER_ROLE_ID)
                    if member and hof_role and hof_role not in member.roles:
                        try:
                            await member.add_roles(hof_role)
                            hof_winners.append(Messages.CHAMPION_HALL_OF_FAME.format(name=name))
                        except discord.Forbidden: pass

            announcement_lines.extend(hof_winners)
            announcement_lines.append(Messages.CHAMPIONS_FOOTER)
            
            # Send to stats channel
            stats_channel = self.bot.get_channel(Config.STATS_CHANNEL_ID)
            if stats_channel:
                await stats_channel.send("\n".join(announcement_lines))
                log.info(f"Weekly Champions announced in {stats_channel.name}")

    @commands.command(name="setup_champions")
    @commands.has_permissions(administrator=True)
    async def setup_champs_cmd(self, ctx):
        """Manual command to trigger role setup."""
        await self._setup_roles(ctx.guild)
        await ctx.send("✅ Champion roles setup complete and config updated!")

    @discord.app_commands.command(name="champion_log", description="Heti bajnoki statisztikák megtekintése.")
    async def champion_log(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        # Get overall stats from DB
        with self.db._get_connection() as conn:
            cursor = conn.execute("""
                SELECT user_id, category, COUNT(*) as wins FROM champion_history 
                WHERE guild_id = ? GROUP BY user_id, category ORDER BY wins DESC
            """, (interaction.guild_id,))
            rows = cursor.fetchall()
        
        if not rows:
            await interaction.followup.send("Még nincsenek rögzített bajnokok a szerveren.")
            return

        # Group by user
        user_wins = {}
        for uid, cat, count in rows:
            if uid not in user_wins: user_wins[uid] = {}
            user_wins[uid][cat] = count
        
        embed = discord.Embed(title="🏆 CHAMPION LOG - Hall of Fame", color=0xFFD700)
        
        count = 0
        for uid, categories in user_wins.items():
            if count >= 10: break
            member = interaction.guild.get_member(uid)
            name = member.display_name if member else f"Ismeretlen ({uid})"
            
            summary = []
            from core.ui_icons import Icons
            for cat, wins in categories.items():
                cat_name = {
                    "spotify": f"{Icons.SPOTIFY} SpotiVibe",
                    "gamer_total": f"{Icons.GAMER} Gamer (H)",
                    "gamer_variety": f"{Icons.VARIETY} Gamer (S)",
                    "streamer": f"{Icons.STREAMER} Streamer"
                }.get(cat, cat)
                summary.append(f"{cat_name}: {wins}x")
            
            embed.add_field(name=name, value=" | ".join(summary), inline=False)
            count += 1
            
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ChampionsCog(bot))
