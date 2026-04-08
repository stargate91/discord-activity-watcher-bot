import discord
import random
import datetime
from discord.ext import commands
from core.logger import log
from config_loader import Config

class BoostCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.bot:
            return
            
        # Ellenőrizzük, hogy a felhasználó most kezdte-e a boostolást
        # premium_since is None (nem boostolt) -> nem None (boostol)
        if before.premium_since is None and after.premium_since is not None:
            await self.handle_boost(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # A Discord rendszer üzeneteket is küld boost esetén. Ezt extra backupként lehet használni.
        # Itt nem duplikáljuk, mert az on_member_update már kezeli, de ha kell, ezen a helyen is reagálhatunk az eredeti rendszerüzenetre!
        pass

    def _fmt(self, text: str, member: discord.Member, count: int) -> str:
        """Sablon helyettesítő: {user.mention}, {user.name}, {guild.name}, {boost_count}"""
        if not text:
            return text
        return (text
            .replace("{user.mention}", member.mention)
            .replace("{user.name}", member.name)
            .replace("{guild.name}", member.guild.name)
            .replace("{boost_count}", str(count))
        )

    def _resolve_icon(self, value: str, member: discord.Member) -> str | None:
        """Feloldja a {user.avatar} / {guild.icon} sablonokat URL-re."""
        if not value:
            return None
        if value == "{user.avatar}":
            return member.display_avatar.url if member.display_avatar else None
        if value == "{guild.icon}":
            return member.guild.icon.url if member.guild.icon else None
        return value

    def _parse_color(self, color_str: str) -> int:
        color_str = str(color_str)
        if color_str.startswith("#"):
            color_str = "0x" + color_str[1:]
        return int(color_str, 16)

    async def handle_boost(self, member: discord.Member):
        boost_config = Config.BOOST
        if not boost_config or not boost_config.get("enabled", False):
            return

        channel_id = boost_config.get("channel_id")
        if not channel_id:
            return

        guild = member.guild
        channel = guild.get_channel(channel_id)
        if not channel:
            log.warning(f"Boost channel {channel_id} not found in {guild.name}")
            return

        # Components V2 mód ellenőrzése
        v2_config = boost_config.get("components_v2", {})
        if v2_config.get("enabled", False):
            await self._send_v2(channel, member, boost_config, v2_config)
        else:
            await self._send_embed(channel, member, boost_config)

    # ─── Hagyományos Embed mód ───────────────────────────────────────────
    async def _send_embed(self, channel, member: discord.Member, boost_config: dict):
        try:
            count = member.guild.premium_subscription_count or 0
            color = self._parse_color(boost_config.get("color", "0xF47FFF"))
            
            description = self._fmt(boost_config.get("description", ""), member, count)
            
            title = boost_config.get("title", "") if boost_config.get("title") else None
            title_url = boost_config.get("title_url", "") or None
            
            embed = discord.Embed(
                title=title,
                url=title_url,
                description=description or None,
                color=color
            )
            
            # Timestamp (opcionális)
            if boost_config.get("show_timestamp", False):
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            
            # Header (Author)
            header_text = boost_config.get("header_text", "")
            if header_text:
                header_text = self._fmt(header_text, member, count)
                header_icon = self._resolve_icon(boost_config.get("header_icon", ""), member)
                header_url = boost_config.get("header_url", "") or None
                embed.set_author(name=header_text, icon_url=header_icon, url=header_url)
            
            # Thumbnail
            thumb = boost_config.get("thumbnail", "")
            thumb_url = self._resolve_icon(thumb, member)
            if thumb_url:
                embed.set_thumbnail(url=thumb_url)
                
            # Egyedi mezők (Fields)
            fields = boost_config.get("fields", [])
            for field in fields:
                f_name = field.get("name", "")
                f_val = field.get("value", "")
                if f_name and f_val:
                    embed.add_field(
                        name=self._fmt(f_name, member, count),
                        value=self._fmt(f_val, member, count),
                        inline=field.get("inline", False)
                    )

            # Nagy kép (opcionális, véletlenszerű ha lista)
            images = boost_config.get("images", [])
            img = ""
            if isinstance(images, list) and images:
                img = random.choice(images)
            elif isinstance(images, str) and images:
                img = images
            if img:
                embed.set_image(url=img)

            # Footer
            footer_text = boost_config.get("footer_text", "")
            if footer_text:
                footer_text = self._fmt(footer_text, member, count)
                footer_icon = self._resolve_icon(boost_config.get("footer_icon", ""), member)
                embed.set_footer(text=footer_text, icon_url=footer_icon)

            content_text = self._fmt(boost_config.get("message_content", ""), member, count) or None

            await channel.send(content=content_text, embed=embed)
            log.info(f"Sent boost embed for {member.name} (ID: {member.id}) in {member.guild.name}")
            
        except Exception as e:
            log.error(f"Failed to send boost embed: {e}")

    # ─── Components V2 (LayoutView) mód ──────────────────────────────────
    async def _send_v2(self, channel, member: discord.Member, boost_config: dict, v2_config: dict):
        try:
            count = member.guild.premium_subscription_count or 0
            color = self._parse_color(v2_config.get("accent_color", boost_config.get("color", "0xF47FFF")))

            # A LayoutView-t dinamikusan építjük fel
            view = discord.ui.LayoutView()

            # Container: ez az "embed-szerű" kártya szegéllyel
            container = discord.ui.Container(accent_colour=discord.Colour(color))

            # Sections: szöveg + opcionális thumbnail/gomb
            for section_cfg in v2_config.get("sections", []):
                texts = section_cfg.get("texts", [])
                text_displays = []
                for t in texts:
                    formatted = self._fmt(t, member, count)
                    if formatted:
                        text_displays.append(discord.ui.TextDisplay(formatted))
                
                if not text_displays:
                    continue

                acc_type = section_cfg.get("accessory_type", "")
                acc_url = self._resolve_icon(section_cfg.get("accessory_url", ""), member)
                
                accessory = None
                if acc_type == "thumbnail" and acc_url:
                    accessory = discord.ui.Thumbnail(acc_url)
                
                if accessory:
                    section = discord.ui.Section(*text_displays, accessory=accessory)
                else:
                    section = discord.ui.Section(*text_displays)
                container.add_item(section)

            # Separator (opcionális vonal)
            if v2_config.get("separator", False):
                container.add_item(discord.ui.Separator(spacing=discord.SeparatorSpacing.small))

            # Media Gallery: képek (random vagy mind)
            gallery_images = v2_config.get("gallery_images", [])
            if gallery_images:
                if v2_config.get("gallery_random", True):
                    selected = [random.choice(gallery_images)]
                else:
                    selected = gallery_images
                
                items = [discord.MediaGalleryItem(url) for url in selected]
                container.add_item(discord.ui.MediaGallery(*items))

            # Bottom texts: a kép alatti szövegek (ami embed-del nem lehetséges!)
            for bt in v2_config.get("bottom_texts", []):
                formatted = self._fmt(bt, member, count)
                if formatted:
                    container.add_item(discord.ui.TextDisplay(formatted))

            view.add_item(container)

            # Buttons: link gombok (ActionRow-ban, a containeren kívül)
            buttons_cfg = v2_config.get("buttons", [])
            valid_buttons = [b for b in buttons_cfg if b.get("url")]
            if valid_buttons:
                action_row = discord.ui.ActionRow()
                for btn_cfg in valid_buttons:
                    label = self._fmt(btn_cfg.get("label", "Link"), member, count)
                    emoji = btn_cfg.get("emoji", None) or None
                    action_row.add_item(discord.ui.Button(
                        style=discord.ButtonStyle.link,
                        label=label,
                        url=btn_cfg["url"],
                        emoji=emoji
                    ))
                view.add_item(action_row)

            await channel.send(view=view)
            log.info(f"Sent boost V2 layout for {member.name} (ID: {member.id}) in {member.guild.name}")

        except Exception as e:
            log.error(f"Failed to send boost V2 message: {e}")

async def setup(bot):
    await bot.add_cog(BoostCog(bot))

