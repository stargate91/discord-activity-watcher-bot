import discord
from discord.ext import tasks, commands
from discord import app_commands
import datetime
import asyncio
import os
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
        await self.tree.sync()
        print("Slash commands synced.")

bot = CheekyBot()

# Track voice session start times: {user_id: join_timestamp}
voice_start_times = {}

# Franchise mapping: {substring_in_game_name: role_name_suffix}
GAME_FRANCHISES = {
    "Counter-Strike": "CS2",
    "The Sims": "Sims",
    "Apex Legends": "Apex Legends",
    "FINAL FANTASY": "Final Fantasy",
    "Age of Empires": "Age of Empires",
    "Overwatch": "Overwatch",
    "Jurassic World Evolution": "Jurassic World Evolution",
    "Dota": "Dota 2",
    "League of Legends": "League of Legends",
    "World of Warcraft": "World of Warcraft",
    "Space Engineers": "Space Engineers",
    "Fortnite": "Fortnite",
    "Stellaris": "Stellaris",
    "EVE Online": "EVE Online",
    "Valorant": "Valorant",
    "Minecraft": "Minecraft"
}

def log_role_assignment(member, role_name):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{now}] {member} ({member.id}) -> {role_name}\n"
    with open("role_log.txt", "a", encoding="utf-8") as f:
        f.write(line)

@bot.event
async def on_presence_update(before, after):
    """Automatically assigns roles based on the game franchise being played."""
    if after.bot or not after.guild: return
    for activity in after.activities:
        if activity.type == discord.ActivityType.playing:
            base_name = activity.name
            for franchise_key, role_suffix in GAME_FRANCHISES.items():
                if franchise_key.lower() in activity.name.lower():
                    base_name = role_suffix
                    break
            target_role_name = f"Player: {base_name}"
            role = discord.utils.get(after.guild.roles, name=target_role_name)
            if role and role not in after.roles:
                try: 
                    await after.add_roles(role)
                    print(f"Assigned {target_role_name} to {after.name}")
                    log_role_assignment(after, target_role_name)
                except discord.Forbidden: pass

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
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Looking for slackers... 🤫"))
    print(f"Bot started as {bot.user}")
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
            if start:
                mins = (datetime.datetime.now(datetime.timezone.utc) - start).total_seconds() / 60
                if mins > 0: db.add_voice_minutes(member.id, member.guild.id, mins)
        
        # If they joined or moved to a new channel, start recording
        if after.channel is not None:
            voice_start_times[member.id] = datetime.datetime.now(datetime.timezone.utc)
            await handle_member_activity(member)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.guild_id:
        guild = bot.get_guild(payload.guild_id)
        if not guild: return
        member = payload.member or await guild.fetch_member(payload.user_id)
        if member: await handle_member_activity(member, event_type="reaction")

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

# --- COMMANDS ---

@bot.command()
@commands.is_owner()
async def sync(ctx):
    """Szinkronizálja a parancsokat az aktuális szerverre (azonnali frissítés)."""
    bot.tree.copy_global_to(guild=ctx.guild)
    synced = await bot.tree.sync(guild=ctx.guild)
    await ctx.send(f"✅ Sikeresen szinkronizáltam {len(synced)} slash parancsot ezen a szerveren!")

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
    
    embed = discord.Embed(title=f"🏆 {title_text}", color=0xFFD700, timestamp=datetime.datetime.now())
    embed.set_footer(text="Pontozás: Üzi: 10 | Reakció: 5 | Voice: 2/perc")
    
    if not top_10:
        embed.description = "Nincs adat ehhez az időszakhoz."
    else:
        desc = ""
        for i, (uid, pts, stats) in enumerate(top_10, 1):
            m = interaction.guild.get_member(uid)
            name = m.mention if m else f"Ismeretlen ({uid})"
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i}.**")
            desc += f"{medal} {name} - **{pts} pont**\n┗ `💬 {stats['messages']} | 🎭 {stats['reactions']} | 🎙️ {int(stats['voice'])} perc`\n"
        embed.description = desc

    # EPHEMERAL: Csak aki hívta látja
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    await interaction.channel.send(file=discord.File(filename)) # A fájlt mindenki látja az admin csatiban, de a szöveg el van rejtve
    os.remove(filename)

@bot.tree.command(name="game_role_report", description="[Admin Channel] Letölti a játékos-rang kiosztások naplóját.")
async def game_role_report(interaction: discord.Interaction):
    if Config.ADMIN_CHANNEL_ID != 0 and interaction.channel_id != Config.ADMIN_CHANNEL_ID:
        await interaction.response.send_message(f"Ez a parancs csak az admin csatornában használható: <#{Config.ADMIN_CHANNEL_ID}>", ephemeral=True)
        return
    
    if not os.path.exists("role_log.txt") or os.path.getsize("role_log.txt") == 0:
        await interaction.response.send_message("Még nincs bejegyzés a naplóban.", ephemeral=True)
        return

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    await interaction.response.send_message(f"Itt a játékos-rang napló ({now_str}):", file=discord.File("role_log.txt", filename=f"role_log_{now_str}.txt"), ephemeral=True)

# Run Bot
if __name__ == "__main__":
    if not Config.validate(): bot.run(Config.TOKEN)
    else: print("Config Error")
