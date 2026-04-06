import discord
import datetime
from discord.ui import LayoutView, Container, Section, TextDisplay, Thumbnail, Separator, ActionRow, Button, Modal, TextInput
from config_loader import Config
from core.messages import Messages

class ModernLeaderboardView(discord.ui.LayoutView):
    # This is the class that builds the list of top players (the leaderboard)
    def __init__(self, items, timeframe, guild, user_data=None, show_user=False, static=False, shared_by=None):
        super().__init__()
        self.guild = guild
        self.timeframe = timeframe
        self.user_data = user_data # (user_obj, points, stats, rank)
        self.show_user = show_user
        self.static = static
        self.shared_by = shared_by
        self.setup_layout(items)

    def setup_layout(self, items):
        # This part puts together the title, the list of names with medals, and the buttons
        title_text = Messages.get_lb_title(self.timeframe)

        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_PRIMARY))
        if self.shared_by:
            container.add_item(discord.ui.TextDisplay(Messages.LB_SHARED_BY.format(user=self.shared_by)))
            container.add_item(discord.ui.Separator())

        container.add_item(discord.ui.TextDisplay(f"# {title_text}"))
        container.add_item(discord.ui.Separator())
        
        if not items:
            container.add_item(discord.ui.TextDisplay(Messages.LB_EMPTY))
        else:
            for i, (uid, pts, stats) in enumerate(items, 1):
                m = self.guild.get_member(uid)
                if self.static:
                    name = f"**{m.display_name}**" if m else Messages.LB_UNKNOWN_USER.format(id=uid)
                else:
                    name = m.mention if m else Messages.LB_UNKNOWN_USER.format(id=uid)
                
                from core.ui_icons import Icons
                medal = {1: Icons.MEDAL_1, 2: Icons.MEDAL_2, 3: Icons.MEDAL_3}.get(i, f"**{i:02d}.**")
                
                info = f"{medal} {name} - **{pts:,.2f} {Messages.LB_POINTS}**\n╰ `M: {stats['messages']} | R: {stats['reactions']} | V: {int(stats['voice'])}p | Me: {stats['media']} | S: {int(stats['stream'])}p`"
                container.add_item(discord.ui.TextDisplay(info))
                
                if i < len(items):
                    container.add_item(discord.ui.Separator())
        
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(Messages.LB_FOOTER_POINTS))
        
        if self.static:
            self.add_item(container)
            return

        # Interactivity: Buttons for timeframe switching
        row = discord.ui.ActionRow()
        for tf, label in [("weekly", Messages.BTN_WEEKLY), ("monthly", Messages.BTN_MONTHLY), ("alltime", Messages.BTN_ALLTIME)]:
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"top:{self.timeframe}:{tf}")
            if tf == self.timeframe:
                btn.style = discord.ButtonStyle.primary
                btn.disabled = True
            row.add_item(btn)
        
        btn_me = discord.ui.Button(label=Messages.BTN_MY_RANK, style=discord.ButtonStyle.secondary, custom_id=f"top:{self.timeframe}:show_me")
        row.add_item(btn_me)

        btn_share = discord.ui.Button(label=Messages.BTN_SHARE, style=discord.ButtonStyle.success, custom_id=f"top:{self.timeframe}:share")
        row.add_item(btn_share)

        container.add_item(row)
        self.add_item(container)

class ModernProfileView(discord.ui.LayoutView):
    # This is the class that builds the profile card when you check someone's stats
    def __init__(self, user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, 
                 joined_at=None, tenure_days=0, efficiency=0, chart_url=None, timeframe="me", static=False, shared_by=None):
        super().__init__()
        self.timeframe = timeframe
        self.static = static
        self.shared_by = shared_by
        # Store for sharing
        self.user_data_full = (user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, joined_at, tenure_days, efficiency)
        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_PRIMARY))
        
        if self.shared_by:
            container.add_item(discord.ui.TextDisplay(Messages.PROFILE_SHARED_BY.format(user=self.shared_by)))
            container.add_item(discord.ui.Separator())

        # 1. Header: Show the user's name, rank and their profile picture
        container.add_item(discord.ui.Section(
            f"# {user.display_name} • #{rank}. {Messages.PROFILE_RANK}\n{Messages.PROFILE_SUBTITLE}",
            accessory=discord.ui.Thumbnail(user.display_avatar.url)
        ))
        
        container.add_item(discord.ui.Separator())
        
        stats_text = (
            Messages.STAT_TOTAL_SCORE.format(points=f"{points:,.2f}") + "\n" +
            Messages.STAT_DETAILS.format(
                msg=data.get('message_count', 0), 
                reac=data.get('reaction_count', 0), 
                media=data.get('media_count', 0),
                voice=int(data.get('voice_minutes', 0)),
                stream=int(data.get('stream_minutes', 0))
            ) + "\n"
        )
        if data.get('spotify_minutes', 0) > 0:
            stats_text += Messages.STAT_SPOTIFY.format(spotify=int(data['spotify_minutes'])) + "\n"
        
        container.add_item(discord.ui.TextDisplay(Messages.SECTION_ACTIVITY + "\n" + stats_text))
        
        # 3. Timing: Show when they were last active, their daily average and avg voice session
        last_active_str = data["last_active"].strftime("%Y-%m-%d %H:%M")
        timing_text = (
            Messages.STAT_LAST_ACTIVE.format(time=last_active_str) + "\n" +
            Messages.STAT_DAILY_AVG.format(avg=avg_daily) + "\n" +
            Messages.STAT_AVG_VOICE.format(avg=avg_voice)
        )
        container.add_item(discord.ui.TextDisplay(Messages.SECTION_STATS + "\n" + timing_text))
        
        # 4. Social: Show favorite channel, emoji and best friend
        social_lines = []
        if social["top_channel"]:
            ch = user.guild.get_channel(social['top_channel'])
            name = f"#{ch.name}" if ch else f"#{social['top_channel']}"
            if self.static:
                social_lines.append(Messages.SOCIAL_FAV_ROOM_STATIC.format(name=name))
            else:
                social_lines.append(Messages.SOCIAL_FAV_ROOM.format(id=social['top_channel']))
        if social["top_emoji"]:
            social_lines.append(Messages.SOCIAL_FAV_EMOJI.format(emoji=social['top_emoji']))
        if social["top_target"]:
            target = user.guild.get_member(social['top_target'])
            name = f"**{target.display_name}**" if target else f"**{social['top_target']}**"
            if self.static:
                social_lines.append(Messages.SOCIAL_MAIN_TARGET_STATIC.format(name=name))
            else:
                social_lines.append(Messages.SOCIAL_MAIN_TARGET.format(id=social['top_target']))
        if partners:
            for pid, _ in partners[:1]:
                p = user.guild.get_member(pid)
                name = f"**{p.display_name}**" if p else f"**{pid}**"
                if self.static:
                    social_lines.append(Messages.SOCIAL_BEST_FRIEND_STATIC.format(name=name))
                else:
                    social_lines.append(Messages.SOCIAL_BEST_FRIEND.format(id=pid))
        
        if social_lines:
            container.add_item(discord.ui.TextDisplay(Messages.SECTION_COMMUNITY + "\n" + "\n".join(social_lines)))
        
        # 5. Veteran: Show how long they have been on the server
        if joined_at:
            join_str = joined_at.strftime("%Y-%m-%d")
            vet_text = (
                Messages.STAT_JOIN_DATE.format(date=join_str) + "\n" +
                Messages.STAT_TENURE.format(days=tenure_days) + "\n" +
                Messages.STAT_LOYALTY.format(efficiency=f"{efficiency:.2f}")
            )
            container.add_item(discord.ui.TextDisplay(Messages.SECTION_VETERAN + "\n" + vet_text))
 
        # 6. Games: Show the top 3 games they have played the most
        if top_games:
            games_text = " | ".join([f"`{g[0].replace(Config.GAME_ROLE_PREFIX, '')}` ({int(g[1] or 0)}p)" for g in top_games])
            container.add_item(discord.ui.TextDisplay(Messages.SECTION_GAMES + "\n" + games_text))
        
        # 7. Activity Chart: Show the 7-day points graph
        if chart_url:
            container.add_item(discord.ui.Separator())
            # Fixed double emoji: SECTION_ACTIVITY usually already contains the bar chart icon if configured,
            # but user specifically asked for 1 emoji only.
            container.add_item(discord.ui.TextDisplay(f"{Messages.SECTION_ACTIVITY} (7D)"))
            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(chart_url)))

        if self.static:
            self.add_item(container)
            return

        container.add_item(discord.ui.Separator())
        
        # 6. Buttons: Add buttons so you can switch between Weekly/Monthly stats or share the profile
        row = discord.ui.ActionRow()
        for tf, label in [("weekly", Messages.BTN_WEEKLY), ("monthly", Messages.BTN_MONTHLY), ("alltime", Messages.BTN_ALLTIME)]:
            btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"top:{self.timeframe}:{tf}")
            row.add_item(btn)
        
        btn_me = discord.ui.Button(label=Messages.BTN_MY_RANK, style=discord.ButtonStyle.primary, custom_id=f"top:{self.timeframe}:show_me", disabled=True)
        row.add_item(btn_me)
        
        btn_share = discord.ui.Button(label=Messages.BTN_SHARE, style=discord.ButtonStyle.success, custom_id=f"top:{self.timeframe}:share")
        row.add_item(btn_share)

        container.add_item(row)
        self.add_item(container)

class ModernInfoView(discord.ui.LayoutView):
    # This class builds a beautiful introduction card for the bot
    def __init__(self, guild):
        super().__init__()
        bot_member = guild.me
        bot_name = bot_member.display_name
        
        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_PRIMARY))
        
        # Header with the bot's server nickname and profile picture
        container.add_item(discord.ui.Section(
            f"# {Messages.INFO_TITLE.format(bot_name=bot_name)}",
            accessory=discord.ui.Thumbnail(bot_member.display_avatar.url)
        ))
        
        container.add_item(discord.ui.Separator())
        
        # A short description of what the bot does
        container.add_item(discord.ui.TextDisplay(Messages.INFO_DESC.format(bot_name=bot_name)))
        
        container.add_item(discord.ui.Separator())
        
        # Listing the main features and commands
        inactive_role = guild.get_role(Config.STAGE_1_ROLE_ID)
        role_mention = inactive_role.mention if inactive_role else "@deleted-role"
        
        container.add_item(discord.ui.TextDisplay(
            Messages.INFO_FEATURES_TITLE + "\n" + 
            Messages.INFO_FEATURES_DESC.format(role=role_mention)
        ))
        
        container.add_item(discord.ui.Separator())
        
        # A nice footer message with a link to the stats channel
        stats_channel = guild.get_channel(Config.STATS_CHANNEL_ID)
        channel_mention = stats_channel.mention if stats_channel else "#deleted-channel"
        container.add_item(discord.ui.TextDisplay(f"*{Messages.INFO_FOOTER.format(channel=channel_mention)}*"))
        
        self.add_item(container)

class ModernDevInfoView(discord.ui.LayoutView):
    # This class builds a premium, structured help menu for bot administrators
    def __init__(self, guild, prefix_cmds, slash_cmds):
        super().__init__()
        
        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_PRIMARY))
        
        # 1. Header with the bot's server nickname and profile picture
        bot_member = guild.me
        bot_name = bot_member.display_name
        container.add_item(discord.ui.Section(
            f"# {Messages.INFO_DEV_TITLE.format(bot_name=bot_name)}",
            accessory=discord.ui.Thumbnail(bot_member.display_avatar.url)
        ))
        
        container.add_item(discord.ui.Separator())
        
        # 2. Prefix Commands Section
        if prefix_cmds:
            container.add_item(discord.ui.TextDisplay(Messages.INFO_DEV_PREFIX.format(suffix=Config.SUFFIX)))
            for name, help_text in prefix_cmds:
                container.add_item(discord.ui.TextDisplay(f"• **{Config.PREFIX}{name}** - *{help_text or '---'}*"))
            
            container.add_item(discord.ui.Separator())

        # 3. Slash Commands Section
        if slash_cmds:
            container.add_item(discord.ui.TextDisplay(Messages.INFO_DEV_SLASH))
            for name, desc, access in slash_cmds:
                container.add_item(discord.ui.TextDisplay(f"• **/{name}** - *{desc}*\n╰ {access}"))
            
            container.add_item(discord.ui.Separator())

        # 4. Footer with admin channel mention and role note
        admin_channel = guild.get_channel(Config.ADMIN_CHANNEL_ID)
        channel_mention = admin_channel.mention if admin_channel else "#deleted-channel"
        footer_text = f"*{Messages.INFO_FOOTER.format(channel=channel_mention)}*\n*{Messages.INFO_DEV_FOOTER_NOTE}*"
        container.add_item(discord.ui.TextDisplay(footer_text))
        
        self.add_item(container)

class ModernChampionsView(discord.ui.LayoutView):
    """
    A premium, high-impact view for announcing the Weekly Champions.
    Uses Sections with Thumbnails for each category to create a stunning layout.
    """
    def __init__(self, guild, champion_data, hof_notices=None, title=None, footer=None, caller_id=None, caller_stats=None):
        super().__init__()
        self.guild = guild
        
        container = discord.ui.Container(accent_color=discord.Color(Config.COLOR_ACCENT))
        
        # 1. Header: Dynamic title from Messages (localized)
        if not title:
            title = Messages.CHAMPIONS_TITLE
        if not footer:
            footer = Messages.CHAMPIONS_FOOTER

        header_text = f"## {title}\n{datetime.datetime.now().strftime('%Y-%m-%d')}"
        container.add_item(discord.ui.Section(
            header_text,
            accessory=discord.ui.Thumbnail(guild.icon.url) if guild.icon else None
        ))
        
        # 2. Winners Section
        winners_count = 0
        winners_list = list(champion_data.items())
        
        if winners_list:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.Separator(visible=False))
        
        for i, (cat_id, (leader_id, value, msg_template)) in enumerate(winners_list):
            member = guild.get_member(leader_id)
            name = f"**{member.display_name}**" if member else f"**{leader_id}**"
            
            # Winner line
            try:
                winner_line = f"### {msg_template.format(name=name, value=value)}"
            except Exception:
                winner_line = f"### {msg_template.replace('{name}', str(name)).replace('{value}', str(value))}"
            
            # Comparison Logic (for /heti_eselyek)
            if caller_id and caller_stats:
                caller_val = caller_stats.get(cat_id, 0)
                if caller_id == leader_id:
                    # They are leading
                    winner_line += f"\n> {Messages.WEEKLY_STANDINGS_KEEP_IT_UP}"
                else:
                    # They are behind
                    # Format value based on category type
                    unit = "p" if cat_id in ["spotify", "gamer_total", "streamer"] else "db"
                    formatted_val = f"{caller_val:.0f}{unit}" if isinstance(caller_val, (int, float)) else f"{caller_val}"
                    diff = value - caller_val
                    formatted_diff = f"{diff:.0f}{unit}" if isinstance(diff, (int, float)) else f"{diff}"
                    
                    winner_line += f"\n> {Messages.WEEKLY_STANDINGS_YOUR_STAT.format(value=formatted_val)}"
                    winner_line += f"\n> {Messages.WEEKLY_STANDINGS_GO_FOR_IT.format(diff=formatted_diff)}"

            container.add_item(discord.ui.TextDisplay(winner_line))
            winners_count += 1
            
        if winners_count == 0:
            container.add_item(discord.ui.Separator())
            container.add_item(discord.ui.TextDisplay(Messages.LB_EMPTY))
        else:
            container.add_item(discord.ui.Separator(visible=False))
            
        # 3. Special Awards (Hall of Fame)
        if hof_notices:
            container.add_item(discord.ui.Separator())
            for notice in hof_notices:
                container.add_item(discord.ui.Separator(visible=False))
                container.add_item(discord.ui.TextDisplay(notice))
                container.add_item(discord.ui.Separator(visible=False))
        
        # 4. Footer: Already handled in init
        container.add_item(discord.ui.Separator())
        container.add_item(discord.ui.TextDisplay(f"\n*{footer}*\n"))
        
        self.add_item(container)

class AltAccountModal(discord.ui.Modal):
    # This modal allows administrators to link an alt/mini account to a main account
    def __init__(self):
        super().__init__(title="Mini Account Összekötés")
        
        self.alt_id = TextInput(
            label="Mini Account Discord ID",
            placeholder="Például: 123456789012345678",
            min_length=17,
            max_length=20,
            required=True
        )
        self.main_id = TextInput(
            label="Fő Account Discord ID",
            placeholder="Például: 987654321098765432",
            min_length=17,
            max_length=20,
            required=True
        )
        
        self.add_item(self.alt_id)
        self.add_item(self.main_id)

    async def on_submit(self, interaction: discord.Interaction):
        # We check if the IDs are actually numbers
        if not self.alt_id.value.isdigit() or not self.main_id.value.isdigit():
            await interaction.response.send_message("❌ Érvénytelen Discord ID (csak számokat tartalmazhat)!", ephemeral=True)
            return
            
        alt_id_int = int(self.alt_id.value)
        main_id_int = int(self.main_id.value)
        
        # Update config and memory
        if Config.update_user_mapping(alt_id_int, main_id_int):
            await interaction.response.send_message(
                f"✅ **Összekötés sikeres!**\nSikeresen összekötöttük a(z) <@{alt_id_int}> fiókot a(z) <@{main_id_int}> fő fiókkal.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Hiba történt a konfiguráció mentése során!", ephemeral=True)
