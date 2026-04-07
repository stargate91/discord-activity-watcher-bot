import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import re
import io
import os
from core.messages import Messages
from core.ui_translate import t
from core.logger import log
from core.ui_utils import get_feedback
from config_loader import Config

class EmojiManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initial format (placeholders to IDs)
        for cmd in self.get_app_commands():
             if not hasattr(cmd, "_raw_desc"):
                 cmd._raw_desc = cmd.description
             
             # Fallback name if bot is not yet logged in
             bname = self.bot.user.name if self.bot.user else "Iris"
             cmd.description = Config.format_desc(cmd._raw_desc, bot_name=bname)

    def refresh_descriptions(self, guild):
        """Re-formats all slash command descriptions using actual names from the guild."""
        bname = self.bot.user.name if self.bot.user else "Iris"
        for cmd in self.get_app_commands():
             if hasattr(cmd, "_raw_desc"):
                 cmd.description = Config.format_desc(cmd._raw_desc, guild, bot_name=bname)

    def _check_perms(self, interaction: discord.Interaction) -> bool:
        """Check if user has Emoji Manager level access based on Discord permissions (Admin/Manage Expressions)."""
        perms = interaction.user.guild_permissions
        return perms.administrator or perms.manage_expressions

    emoji_group = app_commands.Group(name="emoji", description=Messages.CMD_EMOJI_GROUP_DESC)

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
                match = re.search(r'(https://cdn3\.emoji\.gg/(?:emojis|stickers)/[^"\s>]+)', html)
                
                if match:
                    asset_url = match.group(1)
                    # Extract name from title tag
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

    async def fetch_asset_from_url(self, url):
        """Downloads an asset from a direct URL."""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        # Try to guess name from URL
                        name = url.split("/")[-1].split("?")[0].split(".")[0]
                        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
                        if not name: name = "custom_url_asset"
                        return data, name
            except Exception as e:
                log.error(f"EmojiManager: Failed to download from URL {url}: {e}")
        return None, None

    @emoji_group.command(name="add", description=Messages.CMD_ADD_EMOJI_DESC)
    @app_commands.describe(
        type="Emoji or Sticker", 
        asset_id="The ID/Slug from emoji.gg (e.g. 315542-eyes)",
        url="Direct link to the image/gif"
    )
    @app_commands.choices(type=[
        app_commands.Choice(name="Emoji", value="emoji"),
        app_commands.Choice(name="Sticker", value="sticker")
    ])
    async def add_emoji(self, interaction: discord.Interaction, type: str, asset_id: str = None, url: str = None):
        if not self._check_perms(interaction):
            return await interaction.response.send_message(t("ERR_NO_PERMISSION"), ephemeral=True)
        if Config.EMOJI_CHANNEL_ID != 0 and interaction.channel_id != Config.EMOJI_CHANNEL_ID:
            return await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.EMOJI_CHANNEL_ID), ephemeral=True)

        if not asset_id and not url:
            return await interaction.response.send_message(t("ERR_ADD_MISSING_ARGS"), ephemeral=True)
            
        await interaction.response.defer()
        
        data, name = None, None
        if url:
            data, name = await self.fetch_asset_from_url(url)
            if not data:
                return await interaction.followup.send(t("ERR_INVALID_URL"))
        else:
            data, name, _ = await self.fetch_emoji_gg_asset(type, asset_id)
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
                    description=f"Added via Watcher Bot",
                    emoji="✨", # Representation emoji/tag
                    file=file
                )
                msg = t("STICKER_ADDED_SUCCESS", name=sticker.name)
            
            await interaction.followup.send(msg)
            log.info(t("LOG_EMOJI_ADDED", type=type, name=name, guild=interaction.guild.name))
            
        except discord.Forbidden:
            await interaction.followup.send(t("ERR_NO_PERMISSION"))
        except discord.HTTPException as e:
            # Check for specific error codes: 30008 (Emoji limit), 30039 (Sticker limit)
            if e.code in [30008, 30039]:
                await interaction.followup.send(get_feedback('ERR_LIMIT_REACHED'))
            else:
                await interaction.followup.send(get_feedback('ERR_GENERIC', e=e.message))
        except Exception as e:
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e))

    async def asset_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for both emojis and stickers."""
        choices = []
        # Combine emojis and stickers for the search
        all_assets = []
        for e in interaction.guild.emojis:
            all_assets.append(app_commands.Choice(name=f" Emoji: {e.name}", value=e.name))
        for s in interaction.guild.stickers:
            all_assets.append(app_commands.Choice(name=f" Sticker: {s.name}", value=s.name))
            
        # Filter based on current input
        filtered = [
            choice for choice in all_assets 
            if current.lower() in choice.name.lower()
        ]
        return filtered[:25]

    @emoji_group.command(name="delete", description=Messages.CMD_DELETE_EMOJI_DESC)
    @app_commands.describe(name="The name of the emoji/sticker to delete")
    @app_commands.autocomplete(name=asset_autocomplete)
    async def delete_emoji(self, interaction: discord.Interaction, name: str):
        if not self._check_perms(interaction):
            return await interaction.response.send_message(t("ERR_NO_PERMISSION"), ephemeral=True)
        if Config.EMOJI_CHANNEL_ID != 0 and interaction.channel_id != Config.EMOJI_CHANNEL_ID:
            return await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.EMOJI_CHANNEL_ID), ephemeral=True)

        # The name might come with "Emoji: " or "Sticker: " prefix from autocomplete
        clean_name = name.split(": ")[-1] if ": " in name else name
        
        # Try to find emoji first
        target = discord.utils.get(interaction.guild.emojis, name=clean_name)
        if not target:
            # Try stickers
            target = discord.utils.get(interaction.guild.stickers, name=clean_name)
            
        if not target:
            return await interaction.response.send_message(t("ERR_EMOJI_NOT_FOUND", name=clean_name), ephemeral=True)
        
        await interaction.response.defer()
        
        try:
            old_name = target.name
            await target.delete()
            await interaction.followup.send(t("EMOJI_DELETED_SUCCESS", name=old_name))
            log.info(f"EmojiManager: Deleted asset '{old_name}' from guild {interaction.guild.name}")
        except Exception as e:
            await interaction.followup.send(get_feedback('ERR_GENERIC', e=e))

    async def emoji_only_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for only emojis (for rename and large)."""
        choices = [
            app_commands.Choice(name=e.name, value=e.name)
            for e in interaction.guild.emojis
            if current.lower() in e.name.lower()
        ]
        return choices[:25]

    @emoji_group.command(name="rename", description=Messages.CMD_RENAME_EMOJI_DESC)
    @app_commands.describe(old_emoji="Select the emoji to rename", new_name="The new name")
    @app_commands.autocomplete(old_emoji=emoji_only_autocomplete)
    async def rename_emoji(self, interaction: discord.Interaction, old_emoji: str, new_name: str):
        if not self._check_perms(interaction):
            return await interaction.response.send_message(t("ERR_NO_PERMISSION"), ephemeral=True)
        if Config.EMOJI_CHANNEL_ID != 0 and interaction.channel_id != Config.EMOJI_CHANNEL_ID:
            return await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.EMOJI_CHANNEL_ID), ephemeral=True)

        try:
            # Find the actual guild emoji object
            actual_emoji = discord.utils.get(interaction.guild.emojis, name=old_emoji)
            if not actual_emoji:
                return await interaction.response.send_message(t("ERR_EMOJI_NOT_FOUND", name=old_emoji), ephemeral=True)
            
            await interaction.response.defer()
                
            old_name = actual_emoji.name
            # Discord emojinames must be alphanumeric + underscores
            clean_name = re.sub(r'[^a-zA-Z0-9_]', '', new_name)
            await actual_emoji.edit(name=clean_name)
            await interaction.followup.send(t("EMOJI_RENAMED_SUCCESS", old=old_name, new=clean_name))
        except Exception as e:
            if interaction.response.is_done():
                await interaction.followup.send(get_feedback('ERR_GENERIC', e=e))
            else:
                await interaction.response.send_message(get_feedback('ERR_GENERIC', e=e), ephemeral=True)

    @emoji_group.command(name="enlarge", description=Messages.CMD_LARGE_EMOJI_DESC)
    @app_commands.describe(emoji="Select an emoji")
    @app_commands.autocomplete(emoji=emoji_only_autocomplete)
    async def enlarge_emoji(self, interaction: discord.Interaction, emoji: str):
        if Config.EMOJI_CHANNEL_ID != 0 and interaction.channel_id != Config.EMOJI_CHANNEL_ID:
            return await interaction.response.send_message(Messages.ERR_ADMIN_ONLY.format(id=Config.EMOJI_CHANNEL_ID), ephemeral=True)

        # Find emoji by name
        target = discord.utils.get(interaction.guild.emojis, name=emoji)
        if not target:
            return await interaction.response.send_message(t("ERR_EMOJI_NOT_FOUND", name=emoji), ephemeral=True)
            
        embed = discord.Embed(title=f":{target.name}:")
        embed.set_image(url=target.url)
        await interaction.response.send_message(embed=embed)

    @emoji_group.command(name="list", description=Messages.CMD_LIST_EMOJIS_DESC)
    async def list_emojis(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
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
        
        # Emoji field: String length must be < 1024
        emoji_list_trimmed = []
        current_len = 0
        for e in emojis:
            e_str = str(e) + " "
            if current_len + len(e_str) > 950: # Leave room for "and more"
                break
            emoji_list_trimmed.append(str(e))
            current_len += len(e_str)
        
        emoji_text = " ".join(emoji_list_trimmed)
        if emoji_count > len(emoji_list_trimmed):
            emoji_text += f"\n... and {emoji_count - len(emoji_list_trimmed)} more"
            
        if not emoji_text: emoji_text = "None"
        embed.add_field(
            name=t("EMOJI_LIST_TITLE", count=emoji_count, limit=emoji_limit),
            value=emoji_text,
            inline=False
        )
        
        # Sticker field: String length must be < 1024
        sticker_list_trimmed = []
        current_len = 0
        for s in stickers:
            s_str = s.name + ", "
            if current_len + len(s_str) > 950:
                break
            sticker_list_trimmed.append(s.name)
            current_len += len(s_str)

        sticker_text = ", ".join(sticker_list_trimmed)
        if sticker_count > len(sticker_list_trimmed):
            sticker_text += f"\n... and {sticker_count - len(sticker_list_trimmed)} more"

        if not sticker_text: sticker_text = "None"
        embed.add_field(
            name=t("STICKER_LIST_TITLE", count=sticker_count, limit=sticker_limit),
            value=sticker_text,
            inline=False
        )

        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmojiManager(bot))
