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

        await self._send_embed(channel, member, boost_config)

    # ─── Embed mód ───────────────────────────────────────────────────────
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

async def setup(bot):
    await bot.add_cog(BoostCog(bot))

