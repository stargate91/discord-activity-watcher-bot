import discord
import random
import datetime
import io
from config_loader import Config
from core.logger import log
from core.image_generator import get_welcome_card

class NotificationService:
    @staticmethod
    def _fmt(text: str, member: discord.Member, boost_count: int = 0) -> str:
        if not text:
            return text
        
        guild = member.guild
        member_count = len([m for m in guild.members if not m.bot])
        
        return (text
            .replace("{user.mention}", member.mention)
            .replace("{user.name}", member.name)
            .replace("{user.display_name}", member.display_name)
            .replace("{guild.name}", guild.name)
            .replace("{member_count}", str(member_count))
            .replace("{boost_count}", str(boost_count))
        )

    @staticmethod
    def _resolve_icon(value: str, member: discord.Member) -> str | None:
        if not value:
            return None
        if value == "{user.avatar}":
            return member.display_avatar.url if member.display_avatar else None
        if value == "{guild.icon}":
            return member.guild.icon.url if member.guild.icon else None
        return value

    @staticmethod
    def _parse_color(color_str: str) -> int:
        color_str = str(color_str)
        if color_str.startswith("#"):
            color_str = "0x" + color_str[1:]
        try:
            return int(color_str, 16)
        except:
            return 0x3498DB

    @classmethod
    async def send_notification(cls, member: discord.Member, config: dict, mode_override: str = None):
        if not config or not config.get("enabled", False):
            return

        channel_id = config.get("channel_id")
        if not channel_id:
            return

        channel = member.guild.get_channel(channel_id)
        if not channel:
            log.warning(f"Notification channel {channel_id} not found in {member.guild.name}")
            return

        mode = mode_override or config.get("mode", "image")
        boost_count = member.guild.premium_subscription_count or 0

        if mode == "image":
            await cls._send_image_card(channel, member, config, boost_count)
        else:
            await cls._send_embed(channel, member, config, boost_count)

    @classmethod
    async def _send_image_card(cls, channel, member: discord.Member, config: dict, boost_count: int):
        try:
            greeting_template = config.get("greeting", "")
            greeting = cls._fmt(greeting_template, member, boost_count)
            
            bg_urls = config.get("images", [])
            if not bg_urls and config.get("image"):
                bg_urls = [config.get("image")]

            main_text_template = config.get("card_main_text", "{user.name}")
            main_text = cls._fmt(main_text_template, member, boost_count)
            
            sub_text_template = config.get("card_sub_text", "")
            sub_text = cls._fmt(sub_text_template, member, boost_count)
            
            avatar_url = member.display_avatar.url if member.display_avatar else None
            
            image_buffer = await get_welcome_card(
                avatar_url=avatar_url,
                main_text=main_text,
                sub_text=sub_text,
                bg_urls=bg_urls,
                style_config=config
            )
            
            # Extract filename from mode or use generic
            filename = "notification.png"
            file = discord.File(fp=image_buffer, filename=filename)
            await channel.send(content=greeting or None, file=file)
            
        except Exception as e:
            log.error(f"Failed to send image card: {e}")
            # Fallback to simple text if image fails
            await channel.send(content=cls._fmt(config.get("greeting", member.mention), member, boost_count))

    @classmethod
    async def _send_embed(cls, channel, member: discord.Member, config: dict, boost_count: int):
        try:
            color = cls._parse_color(config.get("color", "0x3498DB"))
            
            description = cls._fmt(config.get("description", ""), member, boost_count)
            title = cls._fmt(config.get("title", ""), member, boost_count) if config.get("title") else None
            title_url = config.get("title_url", "") or None
            
            embed = discord.Embed(
                title=title,
                url=title_url,
                description=description or None,
                color=color
            )
            
            if config.get("show_timestamp", False):
                embed.timestamp = datetime.datetime.now(datetime.timezone.utc)
            
            header_text = config.get("header_text", "")
            if header_text:
                header_text = cls._fmt(header_text, member, boost_count)
                header_icon = cls._resolve_icon(config.get("header_icon", ""), member)
                header_url = config.get("header_url", "") or None
                embed.set_author(name=header_text, icon_url=header_icon, url=header_url)
            
            thumb = config.get("thumbnail", "")
            thumb_url = cls._resolve_icon(thumb, member)
            if thumb_url:
                embed.set_thumbnail(url=thumb_url)
                
            fields = config.get("fields", [])
            for field in fields:
                f_name = field.get("name", "")
                f_val = field.get("value", "")
                if f_name and f_val:
                    embed.add_field(
                        name=cls._fmt(f_name, member, boost_count),
                        value=cls._fmt(f_val, member, boost_count),
                        inline=field.get("inline", False)
                    )

            images = config.get("images", [])
            img_url = ""
            if isinstance(images, list) and images:
                img_url = random.choice(images)
            elif isinstance(images, str) and images:
                img_url = images
            
            if img_url and not img_url.startswith("#") and len(img_url) > 8:
                embed.set_image(url=img_url)

            footer_text = config.get("footer_text", "")
            if footer_text:
                footer_text = cls._fmt(footer_text, member, boost_count)
                footer_icon = cls._resolve_icon(config.get("footer_icon", ""), member)
                embed.set_footer(text=footer_text, icon_url=footer_icon)

            greeting = cls._fmt(config.get("greeting", ""), member, boost_count)
            await channel.send(content=greeting or None, embed=embed)
            
        except Exception as e:
            log.error(f"Failed to send notification embed: {e}")
            await channel.send(content=cls._fmt(config.get("greeting", member.mention), member, boost_count))
