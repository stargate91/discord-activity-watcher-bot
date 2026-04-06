import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
import io
from core.messages import Messages
from core.ui_translate import t
from core.logger import log

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initial format (placeholders to IDs)
        for cmd in self.get_app_commands():
             if not hasattr(cmd, "_raw_desc"):
                 cmd._raw_desc = cmd.description
             # Note: We need the config to format, but we'll use a helper if available
             from config_loader import Config
             cmd.description = Config.format_desc(cmd._raw_desc)

    def refresh_descriptions(self, guild):
        """Re-formats all slash command descriptions using actual names from the guild."""
        from config_loader import Config
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild)

    async def fetch_emoji_gg_asset(self, asset_type, asset_id):
        """
        Fetches an emoji or sticker from emoji.gg.
        asset_type: 'emoji' or 'sticker'
        asset_id: slug or numeric ID (e.g. 315542-eyes)
        """
        url = f"https://emoji.gg/{asset_type}/{asset_id}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return None, None, None
                html = await response.text()
                
                # Regex to find CDN image URL (emojis or stickers)
                # Usually: https://cdn3.emoji.gg/emojis/1234_name.png or stickers/1234_name.png
                match = re.search(r'(https://cdn3\.emoji\.gg/(?:emojis|stickers)/[^"\s>]+)', html)
                
                if match:
                    asset_url = match.group(1)
                    # Extract name from title tag: <title>name - Discord Emoji</title>
                    # or from the URL itself if title fails
                    name_match = re.search(r'<title>(.*?) - Discord (?:Emoji|Sticker)</title>', html)
                    name = name_match.group(1).strip().replace(" ", "_") if name_match else asset_id.split("-")[-1]
                    
                    # Clean name (legal Discord chars: alphanumeric and underscore)
                    name = re.sub(r'[^a-zA-Z0-9_]', '', name)
                    if not name: name = "custom_asset"

                    # Download the actual image data
                    async with session.get(asset_url) as img_resp:
                        if img_resp.status == 200:
                            return await img_resp.read(), name, asset_url
        return None, None, None

    @app_commands.command(name="add", description="Add emoji/sticker from emoji.gg")
    @app_commands.describe(type="Emoji or Sticker", asset_id="The ID/Slug from emoji.gg (e.g. 315542-eyes)")
    @app_commands.choices(type=[
        app_commands.Choice(name="Emoji", value="emoji"),
        app_commands.Choice(name="Sticker", value="sticker")
    ])
    @commands.has_permissions(manage_expressions=True)
    async def add_emoji(self, interaction: discord.Interaction, type: str, asset_id: str):
        await interaction.response.defer(ephemeral=True)
        
        data, name, asset_url = await self.fetch_emoji_gg_asset(type, asset_id)
        if not data:
            return await interaction.followup.send(t("ERR_FETCH_EMOJI_GG"))
        
        try:
            if type == "emoji":
                emoji = await interaction.guild.create_custom_emoji(name=name, image=data)
                msg = t("EMOJI_ADDED_SUCCESS", name=emoji.name)
            else:
                # Stickers require a File object and more metadata
                file = discord.File(io.BytesIO(data), filename=f"{name}.png")
                sticker = await interaction.guild.create_sticker(
                    name=name,
                    description=f"Added from emoji.gg ({asset_id})",
                    emoji="✨", # Representation emoji/tag
                    file=file
                )
                msg = t("STICKER_ADDED_SUCCESS", name=sticker.name)
            
            await interaction.followup.send(msg)
            log.info(f"EmojiManager: Added {type} '{name}' to guild {interaction.guild.name}")
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to manage emojis/stickers.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}")

    @app_commands.command(name="delete", description="Delete an emoji or sticker")
    @app_commands.describe(name="The name or specific ID of the emoji/sticker to delete")
    @commands.has_permissions(manage_expressions=True)
    async def delete_emoji(self, interaction: discord.Interaction, name: str):
        # Try to find emoji first
        target = discord.utils.get(interaction.guild.emojis, name=name)
        if not target:
            # Try stickers
            target = discord.utils.get(interaction.guild.stickers, name=name)
            
        if not target:
            return await interaction.response.send_message(t("ERR_EMOJI_NOT_FOUND", name=name), ephemeral=True)
        
        try:
            old_name = target.name
            await target.delete()
            await interaction.response.send_message(t("EMOJI_DELETED_SUCCESS", name=old_name), ephemeral=True)
            log.info(f"EmojiManager: Deleted asset '{old_name}' from guild {interaction.guild.name}")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="rename", description="Rename an emoji")
    @app_commands.describe(old_emoji="Select the emoji to rename", new_name="The new name")
    @commands.has_permissions(manage_expressions=True)
    async def rename_emoji(self, interaction: discord.Interaction, old_emoji: discord.Emoji, new_name: str):
        try:
            old_name = old_emoji.name
            # Discord emojinames must be alphanumeric + underscores
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', new_name)
            await old_emoji.edit(name=clean_name)
            await interaction.response.send_message(t("EMOJI_RENAMED_SUCCESS", old=old_name, new=clean_name), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

    @app_commands.command(name="large", description="Show a large version of an emoji")
    @app_commands.describe(emoji="Select an emoji")
    async def large_emoji(self, interaction: discord.Interaction, emoji: discord.Emoji):
        embed = discord.Embed(title=f":{emoji.name}:")
        embed.set_image(url=emoji.url)
        await interaction.response.send_message(embed=embed)

    list_group = app_commands.Group(name="list", description="List server assets")

    @list_group.command(name="emoji", description="List all server emojis and stickers")
    async def list_emojis(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # Emoji list
        emojis = sorted(guild.emojis, key=lambda x: x.name)
        emoji_limit = guild.emoji_limit
        emoji_count = len(emojis)
        
        # Sticker list
        stickers = sorted(guild.stickers, key=lambda x: x.name)
        sticker_limit = guild.sticker_limit
        sticker_count = len(stickers)

        embed = discord.Embed(title=f"Emoji & Sticker Inventory - {guild.name}", color=discord.Color.blue())
        
        # Emoji field
        emoji_text = " ".join([str(e) for e in emojis[:50]]) + (f"... and {emoji_count-50} more" if emoji_count > 50 else "")
        if not emoji_text: emoji_text = "None"
        embed.add_field(
            name=t("EMOJI_LIST_TITLE", count=emoji_count, limit=emoji_limit),
            value=emoji_text,
            inline=False
        )
        
        # Sticker field
        sticker_text = ", ".join([s.name for s in stickers[:20]]) + (f"... and {sticker_count-20} more" if sticker_count > 20 else "")
        if not sticker_text: sticker_text = "None"
        embed.add_field(
            name=t("STICKER_LIST_TITLE", count=sticker_count, limit=sticker_limit),
            value=sticker_text,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
