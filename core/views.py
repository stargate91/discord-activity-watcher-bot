import discord
import datetime
from discord.ui import LayoutView, Container, Section, TextDisplay, Thumbnail, Separator, ActionRow, Button, Modal, TextInput
from config_loader import Config
from core.messages import Messages
from core.logger import log
from core.ui_translate import t
from core.ui_icons import Icons
from core.ui_utils import get_feedback

class ModernLeaderboardView(discord.ui.LayoutView):
    # This is the special class that builds our beautiful list of top players (the leaderboard)!
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
        # This is where we put everything together: the title, the names with medals, and all the cool buttons!
        title_text = Messages.get_lb_title(self.timeframe)
        container_items = []

        if self.shared_by:
            container_items.append(discord.ui.TextDisplay(Messages.LB_SHARED_BY.format(user=self.shared_by)))
            container_items.append(discord.ui.Separator())

        container_items.append(discord.ui.TextDisplay(f"# {title_text}"))
        container_items.append(discord.ui.Separator())
        
        if not items:
            container_items.append(discord.ui.TextDisplay(Messages.LB_EMPTY))
        else:
            for i, (uid, pts, stats) in enumerate(items, 1):
                m = self.guild.get_member(uid)
                if self.static:
                    name = f"**{m.display_name}**" if m else Messages.LB_UNKNOWN_USER.format(id=uid)
                else:
                    name = m.mention if m else Messages.LB_UNKNOWN_USER.format(id=uid)
                
                from core.ui_icons import Icons
                medal = {1: str(Icons.MEDAL_1), 2: str(Icons.MEDAL_2), 3: str(Icons.MEDAL_3)}.get(i, f"**{i:02d}.**")
                
                info = f"{medal} {name} - **{pts:,.2f} {Messages.LB_POINTS}**\n╰ `M: {stats['messages']} | R: {stats['reactions']} | V: {int(stats['voice'])}p | Me: {stats['media']} | S: {int(stats['stream'])}p`"
                container_items.append(discord.ui.TextDisplay(info))
                
                if i < len(items):
                    container_items.append(discord.ui.Separator())
        
        container_items.append(discord.ui.Separator())
        container_items.append(discord.ui.TextDisplay(Messages.LB_FOOTER_POINTS))
        
        # Interactivity: Buttons for timeframe switching
        if not self.static:
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
            container_items.append(row)

        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)


class ModernProfileView(discord.ui.LayoutView):
    # This is the magic class that builds the gorgeous profile card when you check someone's stats!
    def __init__(self, user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, 
                 joined_at=None, tenure_days=0, efficiency=0, chart_url=None, timeframe="me", static=False, shared_by=None):
        super().__init__()
        self.timeframe = timeframe
        self.static = static
        self.shared_by = shared_by
        # Store for sharing
        self.user_data_full = (user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, avg_voice, joined_at, tenure_days, efficiency)
        container_items = []
        
        if self.shared_by:
            container_items.append(discord.ui.TextDisplay(Messages.PROFILE_SHARED_BY.format(user=self.shared_by)))
            container_items.append(discord.ui.Separator())

        # 1. Header
        container_items.append(discord.ui.Section(
            f"# {user.display_name} • #{rank}. {Messages.PROFILE_RANK}\n{Messages.PROFILE_SUBTITLE}",
            accessory=discord.ui.Thumbnail(user.display_avatar.url)
        ))
        container_items.append(discord.ui.Separator())
        
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
        
        container_items.append(discord.ui.TextDisplay(Messages.SECTION_ACTIVITY + "\n" + stats_text))
        
        # 3. Timing/Activity
        last_active_str = data["last_active"].strftime("%Y-%m-%d %H:%M")
        timing_text = (
            Messages.STAT_LAST_ACTIVE.format(time=last_active_str) + "\n" +
            Messages.STAT_DAILY_AVG.format(avg=avg_daily) + "\n" +
            Messages.STAT_AVG_VOICE.format(avg=avg_voice)
        )
        container_items.append(discord.ui.TextDisplay(Messages.SECTION_STATS + "\n" + timing_text))
        
        # 4. Community
        social_lines = []
        if social["top_channel"]:
            ch = user.guild.get_channel(social['top_channel'])
            name = f"#{ch.name}" if ch else f"#{social['top_channel']}"
            if self.static: social_lines.append(Messages.SOCIAL_FAV_ROOM_STATIC.format(name=name))
            else: social_lines.append(Messages.SOCIAL_FAV_ROOM.format(id=social['top_channel']))
        if social["top_emoji"]:
            social_lines.append(Messages.SOCIAL_FAV_EMOJI.format(emoji=social['top_emoji']))
        if partners:
            for pid, _ in partners[:1]:
                p = user.guild.get_member(pid)
                name = f"**{p.display_name}**" if p else f"**{pid}**"
                if self.static: social_lines.append(Messages.SOCIAL_BEST_FRIEND_STATIC.format(name=name))
                else: social_lines.append(Messages.SOCIAL_BEST_FRIEND.format(id=pid))
        
        if social_lines:
            container_items.append(discord.ui.TextDisplay(Messages.SECTION_COMMUNITY + "\n" + "\n".join(social_lines)))
        
        # 5. Veteran
        if joined_at:
            join_str = joined_at.strftime("%Y-%m-%d")
            vet_text = (
                Messages.STAT_JOIN_DATE.format(date=join_str) + "\n" +
                Messages.STAT_TENURE.format(days=tenure_days) + "\n" +
                Messages.STAT_LOYALTY.format(efficiency=f"{efficiency:.2f}")
            )
            container_items.append(discord.ui.TextDisplay(Messages.SECTION_VETERAN + "\n" + vet_text))
 
        # 6. Games
        if top_games:
            games_text = " | ".join([f"`{g[0].replace(Config.GAME_ROLE_PREFIX, '')}` ({int(g[1] or 0)}p)" for g in top_games])
            container_items.append(discord.ui.TextDisplay(Messages.SECTION_GAMES + "\n" + games_text))
        
        # 7. Activity Graph
        if chart_url:
            from core.logger import log
            log.info(f"ModernProfileView setup: chart_url={chart_url}")
            container_items.append(discord.ui.Separator())
            
            # Header
            container_items.append(discord.ui.TextDisplay(f"{Icons.CHART} {Messages.SECTION_ACTIVITY} (7D)"))
            
            mg = discord.ui.MediaGallery()
            mg.add_item(media=chart_url)
            container_items.append(mg)

        # 8. Buttons
        if not self.static:
            container_items.append(discord.ui.Separator())
            row = discord.ui.ActionRow()
            for tf, label in [("weekly", Messages.BTN_WEEKLY), ("monthly", Messages.BTN_MONTHLY), ("alltime", Messages.BTN_ALLTIME)]:
                btn = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary, custom_id=f"top:{self.timeframe}:{tf}")
                row.add_item(btn)
            
            btn_me = discord.ui.Button(label=Messages.BTN_MY_RANK, style=discord.ButtonStyle.primary, custom_id=f"top:{self.timeframe}:show_me", disabled=True)
            row.add_item(btn_me)
            
            btn_share = discord.ui.Button(label=Messages.BTN_SHARE, style=discord.ButtonStyle.success, custom_id=f"top:{self.timeframe}:share")
            row.add_item(btn_share)
            container_items.append(row)

        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)

class ModernInfoView(discord.ui.LayoutView):
    # This class makes a super friendly 'welcome' card that introduces our bot to everyone!
    def __init__(self, guild):
        super().__init__()
        bot_member = guild.me
        bot_name = bot_member.display_name
        
        stats_channel = guild.get_channel(Config.STATS_CHANNEL_ID)
        channel_mention = stats_channel.mention if stats_channel else "#deleted-channel"
        inactive_role = guild.get_role(Config.STAGE_1_ROLE_ID)
        role_mention = inactive_role.mention if inactive_role else "@deleted-role"

        container_items = [
            discord.ui.Section(
                f"# {Messages.INFO_TITLE.format(bot_name=bot_name)}",
                accessory=discord.ui.Thumbnail(bot_member.display_avatar.url)
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(Messages.INFO_DESC.format(bot_name=bot_name)),
            discord.ui.Separator(),
            discord.ui.TextDisplay(
                Messages.INFO_FEATURES_TITLE + "\n" + 
                Messages.INFO_FEATURES_DESC.format(role=role_mention)
            ),
            discord.ui.Separator(),
            discord.ui.TextDisplay(f"*{Messages.INFO_FOOTER.format(channel=channel_mention)}*")
        ]
        
        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)

class ModernDevInfoView(discord.ui.LayoutView):
    # This is the 'secret menu' for bot admins! It shows all the commands they can use.
    def __init__(self, guild, prefix_cmds, slash_cmds):
        super().__init__()
        
        # 1. Header with the bot's server nickname and profile picture
        bot_member = guild.me
        bot_name = bot_member.display_name
        container_items = [
            discord.ui.Section(
                f"# {Messages.INFO_DEV_TITLE.format(bot_name=bot_name)}",
                accessory=discord.ui.Thumbnail(bot_member.display_avatar.url)
            ),
            discord.ui.Separator()
        ]
        
        # 2. Prefix Commands Section
        if prefix_cmds:
            container_items.append(discord.ui.TextDisplay(Messages.INFO_DEV_PREFIX.format(suffix=Config.SUFFIX)))
            for name, help_text in prefix_cmds:
                container_items.append(discord.ui.TextDisplay(f"• **{Config.PREFIX}{name}** - *{help_text or '---'}*"))
            container_items.append(discord.ui.Separator())

        # 3. Slash Commands Section
        if slash_cmds:
            container_items.append(discord.ui.TextDisplay(Messages.INFO_DEV_SLASH))
            for name, desc, access in slash_cmds:
                container_items.append(discord.ui.TextDisplay(f"• **/{name}** - *{desc}*\n╰ {access}"))
            container_items.append(discord.ui.Separator())

        # 4. Footer
        admin_channel = guild.get_channel(Config.ADMIN_CHANNEL_ID)
        channel_mention = admin_channel.mention if admin_channel else "#deleted-channel"
        footer_text = f"*{Messages.INFO_FOOTER.format(channel=channel_mention)}*\n*{Messages.INFO_DEV_FOOTER_NOTE}*"
        container_items.append(discord.ui.TextDisplay(footer_text))
        
        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)

class ModernElitesView(discord.ui.LayoutView):
    """
    This is the big show! We use this to announce our weekly elites in a really cool way!
    """
    def __init__(self, guild, elite_data, hof_notices=None, title=None, footer=None, caller_id=None, caller_stats=None):
        super().__init__()
        try:
            self.setup_layout(guild, elite_data, hof_notices, title, footer, caller_id, caller_stats)
        except Exception as e:
            log.error(f"Error in ModernElitesView init: {e}", exc_info=True)

    def setup_layout(self, guild, elite_data, hof_notices, title, footer, caller_id, caller_stats):
        container_items = []
        
        # 1. Header (Standardized titles)
        title = title or Messages.ELITES_TITLE
        container_items.append(discord.ui.TextDisplay(f"# {title}\n{datetime.datetime.now().strftime('%Y-%m-%d')}"))
        container_items.append(discord.ui.Separator())
        
        # 2. Winners
        winners_list = list(elite_data.items())
        for i, (cat_id, (leader_id, value, msg_template)) in enumerate(winners_list):
            member = guild.get_member(leader_id)
            name = member.display_name if member else f"Ismeretlen ({leader_id})"
            
            winner_line = f"### {msg_template.format(name=name, value=value)}"
            container_items.append(discord.ui.TextDisplay(winner_line))
            
            if i < len(winners_list) - 1:
                container_items.append(discord.ui.Separator())

        # 3. Hall of Fame
        if hof_notices:
            container_items.append(discord.ui.Separator())
            hof_text = "\n".join(hof_notices)
            container_items.append(discord.ui.TextDisplay(f"## {Messages.ELITE_HALL_OF_FAME_TITLE}\n{hof_text}"))

        # 4. Footer
        footer = footer or Messages.ELITES_FOOTER
        container_items.append(discord.ui.Separator())
        container_items.append(discord.ui.TextDisplay(f"*{footer}*"))

        # 5. Build and Add Container
        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)

class AltAccountModal(discord.ui.Modal):
    # This is a special pop-up that lets admins link two accounts together (like a main and a mini account!).
    def __init__(self):
        super().__init__(title=t("MODAL_ALT_TITLE"))
        
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
            await interaction.response.send_message(get_feedback('ERR_INVALID_ID'), ephemeral=True)
            return
            
        alt_id_int = int(self.alt_id.value)
        main_id_int = int(self.main_id.value)
        
        # Update config and memory
        if Config.update_user_mapping(alt_id_int, main_id_int):
            await interaction.response.send_message(
                get_feedback('MODAL_ALT_SUCCESS', alt_id=alt_id_int, main_id=main_id_int),
                ephemeral=True
            )
        else:
            await interaction.response.send_message(get_feedback('ERR_CONFIG_SAVE'), ephemeral=True)

class ModernPaginatorView(discord.ui.LayoutView):
    # This is a cool helper class that lets us flip through many pages of information!
    def __init__(self, page_items, user=None):
        super().__init__()
        self.page_items = page_items # List of lists of items per page
        self.current_page = 0
        self.user = user
        try:
            self.setup_page(is_initial=True)
        except Exception as e:
            log.error(f"Error in ModernPaginatorView init: {e}", exc_info=True)

    def setup_page(self, is_initial=False):
        if not is_initial:
            self.clear_items()
        
        total = len(self.page_items)
        container_items = list(self.page_items[self.current_page])

        # 1. Navigation Row (only if multiple pages)
        if total > 1:
            row = discord.ui.ActionRow()
            
            # Prev Button
            prev_btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary, 
                emoji=Icons.PREV_PAGE, # Use custom icon
                disabled=(self.current_page == 0)
            )
            prev_btn.callback = self.prev_page
            row.add_item(prev_btn)
            
            # Indicator
            indicator = discord.ui.Button(
                style=discord.ButtonStyle.secondary,
                label=f"{self.current_page + 1} / {total}", # Standardized label
                disabled=True
            )
            row.add_item(indicator)
            
            # Next Button
            next_btn = discord.ui.Button(
                style=discord.ButtonStyle.secondary, 
                emoji=Icons.NEXT_PAGE, # Use custom icon
                disabled=(self.current_page == total - 1)
            )
            next_btn.callback = self.next_page
            row.add_item(next_btn)
            
            container_items.append(row)

        # 2. Build Container
        container = discord.ui.Container(*container_items, accent_color=discord.Color(Config.COLOR_PRIMARY))
        self.add_item(container)

    async def prev_page(self, interaction: discord.Interaction):
        if self.user and interaction.user.id != self.user.id:
            return await interaction.response.send_message(t("ERR_NOT_YOUR_BUTTON"), ephemeral=True)
            
        if self.current_page > 0:
            self.current_page -= 1
            self.setup_page()
            try:
                # IMPORTANT: For LayoutView, we must clear components in the message to avoid conflicts
                await interaction.response.edit_message(view=self)
            except Exception as e:
                log.error(f"Paginator Error (Prev): {e}")

    async def next_page(self, interaction: discord.Interaction):
        if self.user and interaction.user.id != self.user.id:
            return await interaction.response.send_message(t("ERR_NOT_YOUR_BUTTON"), ephemeral=True)
            
        if self.current_page < len(self.page_items) - 1:
            self.current_page += 1
            self.setup_page()
            try:
                await interaction.response.edit_message(view=self)
            except Exception as e:
                log.error(f"Paginator Error (Next): {e}")
