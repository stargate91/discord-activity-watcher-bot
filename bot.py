import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import asyncio
import os
from core.logger import log
from db_manager import DBManager
from config_loader import Config

# Initialize Database
db = DBManager()

# Init Intents
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.voice_states = True
intents.reactions = True
intents.message_content = True
intents.presences = True

class CheekyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        
    async def setup_hook(self):
        # Sync Slash Commands
        if Config.GUILD_ID:
            guild = discord.Object(id=Config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info(f"Slash commands synced to guild {Config.GUILD_ID} (Instant).")
        else:
            await self.tree.sync()
            log.info("Slash commands synced globally.")

bot = CheekyBot()

# Track voice session start times: {user_id: join_timestamp}
voice_start_times = {}

# Cache for dynamic game franchises: {substring: role_suffix}
GAME_FRANCHISES = {}

async def load_game_franchises():
    """Loads games from DB and includes hardcoded defaults if DB is empty."""
    global GAME_FRANCHISES
    db_games = db.get_tracked_games()
    
    if not db_games:
        # Fallback to defaults + save them to DB for first run
        defaults = {
            "Counter-Strike": "CS2", "The Sims": "Sims", "Apex Legends": "Apex Legends",
            "FINAL FANTASY": "Final Fantasy", "Age of Empires": "Age of Empires", 
            "Overwatch": "Overwatch", "Jurassic World Evolution": "Jurassic World Evolution",
            "Dota": "Dota 2", "League of Legends": "League of Legends", 
            "World of Warcraft": "World of Warcraft", "Space Engineers": "Space Engineers",
            "Fortnite": "Fortnite", "Stellaris": "Stellaris", "EVE Online": "EVE Online",
            "Valorant": "Valorant", "Minecraft": "Minecraft", "The Bazaar": "The Bazaar"
        }
        for sub, suf in defaults.items():
            db.add_tracked_game(sub, suf)
        GAME_FRANCHISES = defaults
    else:
        GAME_FRANCHISES = db_games
    log.info(f"Loaded {len(GAME_FRANCHISES)} tracked games.")

# --- MODERN UI COMPONENTS (Components V2) ---

class ModernLeaderboardView(discord.ui.LayoutView):
    def __init__(self, title, items, guild):
        super().__init__()
        
        # Gold accent for top 10
        container = discord.ui.Container(accent_color=discord.Color.from_rgb(241, 196, 15))
        container.add_item(discord.ui.TextDisplay(f"# 🏆 {title}"))
        container.add_item(discord.ui.Separator())
        
        if not items:
            container.add_item(discord.ui.TextDisplay("*Nincs elég adat az időszakhoz... Legyél te az első!* 🚀"))
        else:
            for i, (uid, pts, stats) in enumerate(items, 1):
                m = guild.get_member(uid)
                name = m.mention if m else f"Ismeretlen ({uid})"
                plain_name = m.display_name if m else f"Ismeretlen ({uid})"
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i:02d}.**")
                
                info = f"{medal} {name} • **{pts:,} pont**\n╰ `💬 {stats['messages']} | 🎭 {stats['reactions']} | 🎙️ {int(stats['voice'])} perc`"
                
                if i <= 3 and m:
                    # Top 3 uses Section + Avatar for that premium look
                    container.add_item(discord.ui.Section(
                        info,
                        accessory=discord.ui.Thumbnail(m.display_avatar.url)
                    ))
                else:
                    container.add_item(discord.ui.TextDisplay(info))
                
                if i < len(items):
                    container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay("### Pontozás: 💬 10 | 🎭 5 | 🎙️ 2/perc"))
        self.add_item(container)

class ModernProfileView(discord.ui.LayoutView):
    def __init__(self, user, data, points, voice_mins, social, partners, rank, recent_games, avg_daily):
        super().__init__()
        # Elegant Blue accent for profile
        container = discord.ui.Container(accent_color=discord.Color.blue())
        
        # Profile Header with large-ish Avatar
        container.add_item(discord.ui.Section(
            f"# {user.display_name} • #{rank}. Helyezés\nÖsszesített profilod a szerveren.",
            accessory=discord.ui.Thumbnail(user.display_avatar.url)
        ))
        
        container.add_item(discord.ui.Separator())
        
        # Core Stats summary
        stats_text = (
            f"🏆 **Összpontszám:** ### **{points:,}**\n"
            f"💬 **Üzenetek:** `{data['message_count']}`\n"
            f"🎭 **Reakciók:** `{data['reaction_count']}`\n"
            f"🎙️ **Voice idő:** `{int(voice_mins)} perc`"
        )
        container.add_item(discord.ui.TextDisplay(stats_text))
        
        # Activity Timing and Averages
        last_active_str = data["last_active"].strftime("%Y-%m-%d %H:%M")
        timing_text = (
            f"📅 **Utoljára aktív:** `{last_active_str}`\n"
            f"📈 **Napi átlag (30 nap):** `{avg_daily:.2f} üzenet/nap`"
        )
        container.add_item(discord.ui.TextDisplay(timing_text))
        
        # Recent Games
        if recent_games:
            games_text = "🎮 **Legutóbbi játékok:** " + ", ".join([f"`{g}`" for g in recent_games])
            container.add_item(discord.ui.TextDisplay(games_text))
        
        # Social stats section
        social_lines = []
        if social["top_channel"]:
            social_lines.append(f"🏠 **Kedvenc szoba:** <#{social['top_channel']}>")
        if social["top_emoji"]:
            social_lines.append(f"✨ **Kedvenc emoji:** {social['top_emoji']}")
        if social["top_target"]:
            social_lines.append(f"🤝 **Fő célpont:** <@{social['top_target']}>")
        if partners:
            for pid, _ in partners[:1]:
                social_lines.append(f"🫂 **Best Friend (Voice):** <@{pid}>")
        
        if social_lines:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay("### 🤝 Szociális statisztikák (30 nap)\n" + "\n".join(social_lines)))
            
        self.add_item(container)


def log_role_assignment(member, role_name):
    db.log_role(member.id, member.guild.id, role_name)

async def migrate_role_logs():
    """Migrates existing role_log.txt into the database."""
    import re
    if not os.path.exists("role_log.txt"): return
    
    log.info("Migrating role_log.txt to database...")
    pattern = re.compile(r"\[(.*?)\] .*? \((\d+)\) -> (.*)")
    
    with open("role_log.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    count = 0
    for line in lines:
        match = pattern.search(line)
        if match:
            ts_str, uid, role = match.groups()
            # Since we don't have guild_id in the log, we might assume it's the first guild the bot is in, 
            # OR we just use 0 if it's for global history (less ideal but logs don't have it).
            # Actually, we can try to find which guild the user belongs to.
            for guild in bot.guilds:
                if guild.get_member(int(uid)):
                    db.log_role(int(uid), guild.id, role, timestamp=ts_str)
                    count += 1
                    break
    
    if count > 0:
        os.rename("role_log.txt", "role_log_migrated.txt")
        log.info(f"Successfully migrated {count} logs to DB.")

@bot.event
async def on_presence_update(before, after):
    """Automatically assigns roles based on the game franchise AND monitors all play activity."""
    if after.bot or not after.guild: return
    for activity in after.activities:
        if activity.type == discord.ActivityType.playing:
            game_to_log = activity.name
            bot_gave_role = False
            
            # Check if it's a tracked franchise for role assignment
            for franchise_key, role_suffix in GAME_FRANCHISES.items():
                if franchise_key.lower() in activity.name.lower():
                    target_role_name = f"Player: {role_suffix}"
                    game_to_log = target_role_name # Use standardized name
                    role = discord.utils.get(after.guild.roles, name=target_role_name)
                    if role:
                        if role not in after.roles:
                            try: 
                                await after.add_roles(role)
                                log.info(f"Assigned {target_role_name} to {after.name}")
                                log_role_assignment(after, target_role_name)
                                bot_gave_role = True
                            except discord.Forbidden: pass
                    break # Stop at first franchise match
            
            # Log the activity (standardized if it matched, raw if not)
            db.update_game_activity(after.id, after.guild.id, game_to_log, bot_assigned=bot_gave_role)

async def handle_member_activity(member: discord.Member, event_type=None):
    if member.bot: return
    db.update_activity(member.id, member.guild.id)
    if event_type == "message": db.increment_messages(member.id, member.guild.id)
    elif event_type == "reaction": db.increment_reactions(member.id, member.guild.id)
    
    stage1_role, stage2_role = member.guild.get_role(Config.STAGE_1_ROLE_ID), member.guild.get_role(Config.STAGE_2_ROLE_ID)
    if stage1_role and stage1_role in member.roles:
        try:
            if stage2_role and stage2_role not in member.roles: await member.add_roles(stage2_role)
            await member.remove_roles(stage1_role)
            db.set_returned_at(member.id, member.guild.id, datetime.datetime.now(datetime.timezone.utc))
        except discord.Forbidden: pass
    elif stage2_role and stage2_role in member.roles:
        data = db.get_user_data(member.id, member.guild.id)
        if data and data["returned_at"]:
            delta = datetime.datetime.now(datetime.timezone.utc) - data["returned_at"].astimezone(datetime.timezone.utc)
            if 60 <= delta.total_seconds() <= (7 * 24 * 3600):
                try: 
                    await member.remove_roles(stage2_role)
                    db.set_returned_at(member.id, member.guild.id, None)
                except discord.Forbidden: pass

@bot.event
async def on_ready():
    # Set Presence
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Figyelem a lazsálókat... 🤫"))
    # Load Games and Migrate logs
    await load_game_franchises()
    await migrate_role_logs()
    
    log.info(f"Bot started as {bot.user}")
    for guild in bot.guilds:
        for m in guild.members:
            if m.bot: continue
            # Ensure member exists in DB
            if not db.get_user_data(m.id, guild.id):
                db.update_activity(m.id, guild.id)
            # Pick up members already in voice channels
            if m.voice and m.voice.channel:
                voice_start_times[m.id] = datetime.datetime.now(datetime.timezone.utc)
    if not check_inactivity_task.is_running(): check_inactivity_task.start()
    if not cleanup_inactive_roles_task.is_running(): cleanup_inactive_roles_task.start()

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild: return
    await handle_member_activity(message.author, event_type="message")
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot: return
    
    # Handle channel moves, joins, and leaves
    if before.channel != after.channel:
        # If they were in a channel, record the time spent
        if before.channel is not None:
            start = voice_start_times.pop(member.id, None)
            # Skip if it was the AFK channel (extra safety) or if no start time was recorded for it
            if start and before.channel.id != Config.AFK_CHANNEL_ID and before.channel != member.guild.afk_channel:
                now = datetime.datetime.now(datetime.timezone.utc)
                mins = (now - start).total_seconds() / 60
                if mins > 0: 
                    db.add_voice_minutes(member.id, member.guild.id, mins)
                    # Log detailed session
                    db.log_voice_session(member.id, member.guild.id, before.channel.id, start, now, mins)
        
        # If they joined or moved to a new channel, start recording (SKIP if AFK)
        if after.channel is not None and after.channel.id != Config.AFK_CHANNEL_ID and after.channel != member.guild.afk_channel:
            voice_start_times[member.id] = datetime.datetime.now(datetime.timezone.utc)
            await handle_member_activity(member)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id:
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        member = payload.member or await guild.fetch_member(payload.user_id)
        if member: 
            await handle_member_activity(member, event_type="reaction")
            
            # Detailed Reaction Interaction Logging
            try:
                channel = bot.get_channel(payload.channel_id)
                if channel:
                    # Look for message in cache, otherwise fetch it
                    message = discord.utils.get(bot.cached_messages, id=payload.message_id)
                    if not message:
                        message = await channel.fetch_message(payload.message_id)
                    
                    if message and message.author and not message.author.bot:
                        if message.author.id != member.id: # Don't log self-reactions as "interaction"
                            db.log_reaction_interaction(
                                user_id=member.id,
                                target_user_id=message.author.id,
                                guild_id=guild.id,
                                channel_id=channel.id,
                                message_id=payload.message_id,
                                emoji=str(payload.emoji)
                            )
            except (discord.NotFound, discord.Forbidden): pass

@tasks.loop(hours=Config.CHECK_INTERVAL_HOURS) 
async def check_inactivity_task():
    now = datetime.datetime.now(datetime.timezone.utc)
    for guild in bot.guilds:
        r1, r2 = guild.get_role(Config.STAGE_1_ROLE_ID), guild.get_role(Config.STAGE_2_ROLE_ID)
        if not r1: continue
        data = db.get_all_guild_data(guild.id)
        for uid, d in data.items():
            m = guild.get_member(uid)
            if not m: continue
            inactive_days = (now - d["last_active"].astimezone(datetime.timezone.utc)).days
            if inactive_days >= Config.STAGE_1_DAYS:
                if r1 not in m.roles:
                    try:
                        await m.add_roles(r1)
                        if r2 and r2 in m.roles: await m.remove_roles(r2)
                        db.set_returned_at(uid, guild.id, None)
                    except discord.Forbidden: pass
            elif d["returned_at"]:
                if (now - d["returned_at"].astimezone(datetime.timezone.utc)).days >= 7:
                    if r2 and r2 in m.roles:
                        try: await m.remove_roles(r2)
                        except discord.Forbidden: pass
                    db.set_returned_at(uid, guild.id, None)

@tasks.loop(hours=24)
async def cleanup_inactive_roles_task():
    """Eltávolítja a Player rangokat, ha 30 napja nem játszottak az adott játékkal, és a bot adta."""
    for guild in bot.guilds:
        inactive = db.get_inactive_games(guild.id, days=30)
        for uid, role_name in inactive:
            member = guild.get_member(uid)
            if not member: continue
            
            role = discord.utils.get(guild.roles, name=role_name)
            if role and role in member.roles:
                try:
                    await member.remove_roles(role)
                    log.info(f"Removed inactive role {role_name} from {member.name} (30 days inactivity)")
                    db.remove_game_activity(uid, guild.id, role_name)
                    db.log_role(uid, guild.id, role_name, action='REMOVED')
                except discord.Forbidden: pass

# --- SLASH COMMANDS ---

@bot.tree.command(name="top", description="Mutatja a heti, havi vagy összesített toplistát.")
@app_commands.describe(timeframe="Válassz időszakot (weekly, monthly, alltime)")
async def top(interaction: discord.Interaction, timeframe: str = "alltime"):
    days = {"weekly": 7, "monthly": 30, "alltime": None}.get(timeframe.lower(), None)
    title_text = {"weekly": "Heti Top 10", "monthly": "Havi Top 10", "alltime": "Összesített Top 10"}.get(timeframe.lower(), "Top 10")
    
    data = db.get_leaderboard_data(interaction.guild_id, days)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    
    # Add live voice session time
    for uid, start in voice_start_times.items():
        m = interaction.guild.get_member(uid)
        if m and m.guild.id == interaction.guild_id:
            curr_mins = (now_utc - start).total_seconds() / 60
            if uid in data:
                data[uid]["voice"] += curr_mins
            else:
                data[uid] = {"messages": 0, "reactions": 0, "voice": curr_mins}

    scores = []
    for uid, stats in data.items():
        points = (stats["messages"] * 10) + (stats["reactions"] * 5) + (int(stats["voice"]) * 2)
        if points > 0: scores.append((uid, points, stats))
    
    scores.sort(key=lambda x: x[1], reverse=True)
    top_10 = scores[:10]
    
    view = ModernLeaderboardView(title_text, top_10, interaction.guild)
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="me", description="Megmutatja a saját aktivitási statisztikáidat.")
async def me(interaction: discord.Interaction):
    data = db.get_user_data(interaction.user.id, interaction.guild_id)
    if not data:
        await interaction.response.send_message("Még nincs adatod az adatbázisban. Írj pár üzenetet előbb!", ephemeral=True)
        return

    # Add live voice time
    voice_mins = data["voice_minutes"]
    if interaction.user.id in voice_start_times:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        voice_mins += (now_utc - voice_start_times[interaction.user.id]).total_seconds() / 60

    points = (data["message_count"] * 10) + (data["reaction_count"] * 5) + (int(voice_mins) * 2)
    
    # Advanced calculations
    social = db.get_user_social_stats(interaction.user.id, interaction.guild_id, days=30)
    partners = db.get_top_voice_partners(interaction.user.id, interaction.guild_id, days=30)
    recent_games = db.get_user_recent_games(interaction.user.id, interaction.guild_id, limit=3)
    
    # Calculate Rank (All time)
    all_data = db.get_leaderboard_data(interaction.guild_id)
    all_scores = []
    for uid, s in all_data.items():
        p = (s["messages"] * 10) + (s["reactions"] * 5) + (int(s["voice"]) * 2)
        all_scores.append((uid, p))
    all_scores.sort(key=lambda x: x[1], reverse=True)
    rank = next((i for i, (uid, _) in enumerate(all_scores, 1) if uid == interaction.user.id), "N/A")
    
    # Calculate Daily Average (30 days)
    monthly_data = db.get_leaderboard_data(interaction.guild_id, days=30)
    user_monthly = monthly_data.get(interaction.user.id, {"messages":0})
    avg_daily = user_monthly["messages"] / 30
    
    view = ModernProfileView(interaction.user, data, points, voice_mins, social, partners, rank, recent_games, avg_daily)
    await interaction.response.send_message(view=view, ephemeral=True)

@bot.tree.command(name="status_report", description="[Admin Channel] Generál egy részletes TXT jelentést.")
async def status_report_slash(interaction: discord.Interaction):
    if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
        await interaction.response.send_message(f"Ez a parancs csak az admin csatornában használható: <#{Config.ADMIN_CHANNEL_ID}>", ephemeral=True)
        return

    await interaction.response.send_message("Status report generálása...", ephemeral=True)
    
    now = datetime.datetime.now(datetime.timezone.utc)
    guild_data = db.get_all_guild_data(interaction.guild_id)
    r1, r2 = interaction.guild.get_role(Config.STAGE_1_ROLE_ID), interaction.guild.get_role(Config.STAGE_2_ROLE_ID)
    lines = [f"--- REPORT: {interaction.guild.name} ---\nGen: {now}\n{'User':<25} | {'Stat':<12} | {'M':<4} | {'R':<4} | {'V':<4} | {'Details'}"]
    
    for m in interaction.guild.members:
        if m.bot: continue
        d = guild_data.get(m.id)
        if not d: continue
        
        # Add live voice time for report
        voice_mins = d['voice_minutes']
        if m.id in voice_start_times:
            voice_mins += (now - voice_start_times[m.id]).total_seconds() / 60
            
        s = "Normal"
        if r1 in m.roles: s = "Stage 1"
        elif r2 in m.roles: s = "Stage 2"
        det = "Inaktív" if s=="Stage 1" else (f"S2-ből: {7-(now-d['returned_at'].astimezone(datetime.timezone.utc)).days} nap" if s=="Stage 2" and d["returned_at"] else f"S1-ig: {Config.STAGE_1_DAYS-(now-d['last_active'].astimezone(datetime.timezone.utc)).days} nap")
        lines.append(f"{str(m)[:25]:<25} | {s:<12} | {d['message_count']:<4} | {d['reaction_count']:<4} | {int(voice_mins):<4} | {det}")
    
    filename = f"report_{interaction.guild_id}.txt"
    with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    await interaction.followup.send(file=discord.File(filename), ephemeral=True) # Csak aki hívta látja a jelentést
    os.remove(filename)

@bot.tree.command(name="game_role_report", description="[Admin Channel] Letölti a játékos-rang kiosztások naplóját.")
async def game_role_report(interaction: discord.Interaction):
    if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
        await interaction.response.send_message(f"Ez a parancs csak az admin csatornában használható: <#{Config.ADMIN_CHANNEL_ID}>", ephemeral=True)
        return
    
    await interaction.response.send_message("Játékos-rang napló generálása...", ephemeral=True)
    
    history = db.get_role_history(interaction.guild_id, limit=300)
    if not history:
        await interaction.followup.send("Még nincs bejegyzés a naplóban.", ephemeral=True)
        return

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    lines = [f"--- JÁTÉKOS-RANG NAPLÓ: {interaction.guild.name} ---\nGen: {now_utc}\n{'Timestamp':<20} | {'User':<25} | {'Státusz':<10} | {'Role'}"]
    
    for uid, role, action, ts in history:
        m = interaction.guild.get_member(uid)
        name = str(m) if m else f"Ismeretlen ({uid})"
        act_text = "ELVÉVE" if action == 'REMOVED' else "ADVA"
        lines.append(f"{ts[:19]:<20} | {name[:25]:<25} | {act_text:<10} | {role}")
    
    filename = f"role_log_{interaction.guild_id}.txt"
    with open(filename, "w", encoding="utf-8") as f: f.write("\n".join(lines))
    
    await interaction.followup.send(file=discord.File(filename), ephemeral=True)
    os.remove(filename)

@bot.tree.command(name="add_game", description="[Admin] Új játék hozzáadása az automata rangosztáshoz.")
@app_commands.describe(search_name="A játék nevének egy része (pl: Minecraft)", role_suffix="A rang vége (példa: 'Minecraft' -> 'Player: Minecraft')")
@commands.has_permissions(administrator=True)
async def add_game(interaction: discord.Interaction, search_name: str, role_suffix: str):
    db.add_tracked_game(search_name, role_suffix)
    await load_game_franchises() # Refresh cache
    await interaction.response.send_message(f"✅ Hozzáadva: Ha a névben szerepel: `{search_name}`, a rang ez lesz: `Player: {role_suffix}`", ephemeral=True)

@bot.tree.command(name="remove_game", description="[Admin] Játék eltávolítása a listából.")
@app_commands.describe(search_name="A pontos keresési kulcsszó (pl: Minecraft)")
@commands.has_permissions(administrator=True)
async def remove_game(interaction: discord.Interaction, search_name: str):
    db.remove_tracked_game(search_name)
    await load_game_franchises() # Refresh cache
    await interaction.response.send_message(f"🗑️ `{search_name}` eltávolítva a figyelési listából.", ephemeral=True)

@bot.tree.command(name="list_games", description="[Admin] Az összes figyelt játék listázása.")
@commands.has_permissions(administrator=True)
async def list_games(interaction: discord.Interaction):
    games = db.get_tracked_games()
    if not games:
        await interaction.response.send_message("Nincsenek figyelt játékok.", ephemeral=True)
        return
    
    desc = "\n".join([f"• `{sub}` ➔ `Player: {suf}`" for sub, suf in games.items()])
    embed = discord.Embed(title="🎮 Figyelt játékok listája", description=desc, color=0x2ecc71)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="game_stats_report", description="[Admin] Játék népszerűségi riport generálása .txt-ben.")
@app_commands.describe(timeframe="Válasz: alltime (összes) vagy monthly (e havi)")
@commands.has_permissions(administrator=True)
async def game_stats_report(interaction: discord.Interaction, timeframe: str = "alltime"):
    if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
        await interaction.response.send_message(f"Ez a parancs csak az admin csatornában használható: <#{Config.ADMIN_CHANNEL_ID}>", ephemeral=True)
        return
        
    await interaction.response.send_message("Riport generálása...", ephemeral=True)
    
    stats = db.get_game_stats_report(interaction.guild_id, timeframe)
    if not stats:
        await interaction.followup.send("Nincsenek adatok a választott időszakhoz.", ephemeral=True)
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    title = "HAVI" if timeframe == "monthly" else "ÖSSZESÍTETT"
    lines = [f"--- JÁTÉK NÉPSZERŰSÉGI RIPORT ({title}) ---", f"Generálva: {now}", ""]
    lines.append(f"{'Játék neve':<40} | {'Egyedi játékosok':<5}")
    lines.append("-" * 60)

    for display_name, count in stats:
        # The SQL query already stripped "Player: ", so we just display it.
        lines.append(f"{display_name[:40]:<40} | {count:<5}")
    
    filename = f"game_stats_{timeframe}_{interaction.guild_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    await interaction.followup.send(
        content=f"📊 Elkészült a(z) `{timeframe}` játék riport ({len(stats)} különböző játék).",
        file=discord.File(filename), 
        ephemeral=True
    )
    os.remove(filename)

# --- SYSTEM ADMINISTRATION ---

@bot.tree.command(name="reset_database", description="[Admin] MINDEN aktivitási adat végleges törlése.")
@commands.has_permissions(administrator=True)
async def reset_database(interaction: discord.Interaction):
    """Közvetlenül törli az adatbázis tartalmát."""
    try:
        db.reset_database()
        await interaction.response.send_message("✅ Az adatbázis sikeresen kiürítve! Minden aktivitási adat törölve lett.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Hiba történt a törlés során: {e}", ephemeral=True)

# Run Bot
if __name__ == "__main__":
    if not Config.validate(): bot.run(Config.TOKEN)
    else: log.error("Config Error")
