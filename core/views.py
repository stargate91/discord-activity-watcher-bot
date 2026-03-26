import discord
from discord.ui import LayoutView, Container, Section, TextDisplay, Thumbnail, Separator, ActionRow, Button
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
                
                medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"**{i:02d}.**")
                
                info = f"{medal} {name} — **{pts:,} {Messages.LB_POINTS}**\n╰ `M: {stats['messages']} | R: {stats['reactions']} | V: {int(stats['voice'])}p`"
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
    def __init__(self, user, data, points, voice_mins, social, partners, rank, top_games, avg_daily, timeframe="alltime", static=False, shared_by=None):
        super().__init__()
        self.timeframe = timeframe
        self.static = static
        self.shared_by = shared_by
        # Store for sharing
        self.user_data_full = (user, data, points, voice_mins, social, partners, rank, top_games, avg_daily)
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
        
        # 2. Activity: Show points, messages, reactions and voice time
        stats_text = (
            Messages.STAT_TOTAL_SCORE.format(points=f"{points:,}") + "\n" +
            Messages.STAT_DETAILS.format(msg=data['message_count'], reac=data['reaction_count'], voice=int(voice_mins))
        )
        container.add_item(discord.ui.TextDisplay(Messages.SECTION_ACTIVITY + "\n" + stats_text))
        
        # 3. Timing: Show when they were last active and their daily average
        last_active_str = data["last_active"].strftime("%Y-%m-%d %H:%M")
        timing_text = (
            Messages.STAT_LAST_ACTIVE.format(time=last_active_str) + "\n" +
            Messages.STAT_DAILY_AVG.format(avg=avg_daily)
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
        
        # 5. Games: Show the top 3 games they have played the most
        if top_games:
            games_text = " — ".join([f"`{g[0].replace('Player: ', '')}` ({int(g[1] or 0)}p)" for g in top_games])
            container.add_item(discord.ui.TextDisplay(Messages.SECTION_GAMES + "\n" + games_text))
        
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
