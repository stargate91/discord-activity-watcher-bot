import discord
from discord.ext import commands
from core.logger import log
from config_loader import Config
from core.messages import Messages
from core.ui_translate import t
import re

class ReactionRoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str = None, emoji: str = None, style: discord.ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(style=style, label=label, emoji=emoji, custom_id=f"rr_btn:{role_id}")

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def cog_load(self):
        # Start the background initialization task
        self.bot.loop.create_task(self.init_reaction_roles())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Global interaction listener to handle persistent reaction role buttons."""
        if interaction.type == discord.InteractionType.component:
            custom_id = interaction.data.get("custom_id", "")
            if custom_id.startswith("rr_btn:"):
                try:
                    role_id = int(custom_id.split(":")[1])
                    guild = interaction.guild
                    if not guild: return
                    
                    role = guild.get_role(role_id)
                    if not role:
                        await interaction.response.send_message(Messages.RR_ERROR_ROLE_NOT_FOUND, ephemeral=True)
                        return
                    
                    if role in interaction.user.roles:
                        await interaction.user.remove_roles(role)
                        await interaction.response.send_message(Messages.RR_ROLE_REMOVED.format(role=role.name), ephemeral=True)
                        log.info(f"ReactionRoleButton: Removed {role.name} from {interaction.user.display_name}")
                    else:
                        await interaction.user.add_roles(role)
                        await interaction.response.send_message(Messages.RR_ROLE_ADDED.format(role=role.name), ephemeral=True)
                        log.info(f"ReactionRoleButton: Added {role.name} to {interaction.user.display_name}")
                except Exception as e:
                    log.error(f"Error handling reaction role button: {e}")
                    if not interaction.response.is_done():
                        await interaction.response.send_message(Messages.RR_ERROR_GENERIC, ephemeral=True)

    CLASS_STYLE_MAP = {
        "primary": discord.ButtonStyle.primary,
        "secondary": discord.ButtonStyle.secondary,
        "success": discord.ButtonStyle.success,
        "danger": discord.ButtonStyle.danger,
        "blurple": discord.ButtonStyle.primary,
        "grey": discord.ButtonStyle.secondary,
        "gray": discord.ButtonStyle.secondary,
        "green": discord.ButtonStyle.success,
        "red": discord.ButtonStyle.danger
    }

    async def init_reaction_roles(self):
        """
        This function runs when the bot starts up. It checks if our special 'Reaction Role' 
        messages are already on Discord, and sends them if they are missing!
        """
        await self.bot.wait_until_ready()
        
        # When bot starts, verify and send reaction role messages if missing
        log.info(f"ReactionRoles initialization triggered. Config count: {len(Config.REACTION_ROLES)}")
        if not Config.REACTION_ROLES:
            return

        for idx, config_data in enumerate(Config.REACTION_ROLES):
            try:
                log.info(f"Processing reaction role {idx}: {config_data.get('identifier')}")
                if config_data.get("enabled", True) is False:
                    continue

                guild = self.bot.get_guild(Config.GUILD_ID)
                if guild:
                    for mapping in config_data.get("mappings", []):
                        # If we don't have the secret ID for a role, we try to find it using its name instead!
                        if mapping.get("role_id", 0) == 0 and mapping.get("role_name"):
                            role = discord.utils.get(guild.roles, name=mapping.get("role_name"))
                            if role:
                                mapping["role_id"] = role.id
                                
                        # We do the same thing for emojis - if the ID is missing, we look for the name!
                        if not mapping.get("emoji") and mapping.get("emoji_name"):
                            emoji_obj = discord.utils.get(guild.emojis, name=mapping.get("emoji_name"))
                            if emoji_obj:
                                mapping["emoji"] = str(emoji_obj)

                identifier = config_data.get("identifier", f"rr_menu_{idx}")
                channel_id = config_data.get("channel_id")
                
                if not channel_id:
                    log.error(f"Reaction role config {identifier} is missing channel_id")
                    continue

                channel = self.bot.get_channel(channel_id)
                if not channel:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                    except (discord.NotFound, discord.Forbidden):
                        log.error(f"Channel {channel_id} is unreachable or forbidden.")
                        continue
                        
                bot_name = guild.me.display_name if guild else self.bot.user.name

                # We check our notebook (the database) to see if we've already sent this message before.
                db_record = await self.db.get_reaction_role_message(guild.id, identifier)

                message = None

                if db_record:
                    saved_channel_id, saved_message_id = db_record
                    if saved_channel_id == channel_id:
                        try:
                            message = await channel.fetch_message(saved_message_id)
                        except (discord.NotFound, discord.Forbidden):
                            pass

                # If we can't find the message, we need to send a brand new one to the channel!
                if message is None:
                    log.info(f"Sending new reaction role message for {identifier}")

                    view = discord.ui.View() # Fallback
                    try:
                        from discord.ui import LayoutView, ActionRow, Container, Section, TextDisplay, Thumbnail, Separator, MediaGallery
                        view = LayoutView()
                        container = Container(accent_color=discord.Color.from_str(config_data.get("color", "0x5865F2")))
                        
                        title = config_data.get("title", "Szerepkörök")
                        if title: title = title.replace("{bot_name}", bot_name)

                        desc = config_data.get("description", "Válaszd ki a szerepeidet!")
                        if desc: desc = desc.replace("{bot_name}", bot_name)
                        
                        content_text = f"## {title}\n{desc}"
                        
                        thumbnail_url = config_data.get("thumbnail")
                        if thumbnail_url:
                            container.add_item(Section(content_text, accessory=Thumbnail(thumbnail_url)))
                        else:
                            container.add_item(TextDisplay(content_text))
                        
                        mappings = config_data.get("mappings", [])
                        mode = config_data.get("mode", "reactions")
                        show_list = config_data.get("show_list", True)
                        list_quote = config_data.get("list_quote", True)
                        list_prefix = config_data.get("list_prefix", "▪️")
                        prefix_fmt = f"{list_prefix} " if list_prefix else ""
                        
                        if mode == "reactions":
                            if show_list and mappings:
                                container.add_item(Separator(visible=False))
                                lines = []
                                for mapping in mappings:
                                    emoji = mapping.get("emoji")
                                    label = mapping.get("label", "")
                                    if emoji:
                                        lines.append(f"{prefix_fmt}{emoji} **{label}**")
                                if lines:
                                    quote_prefix = ">>> " if list_quote else ""
                                    container.add_item(TextDisplay(quote_prefix + "\n".join(lines)))
                        elif mode == "buttons":
                            row_size = min(max(int(config_data.get("row_size", 5)), 1), 5)
                            current_row = ActionRow()
                            for m_idx, mapping in enumerate(mappings):
                                role_id = mapping.get("role_id")
                                if not role_id: continue
                                if m_idx > 0 and m_idx % row_size == 0:
                                    container.add_item(current_row)
                                    current_row = ActionRow()
                                emoji = mapping.get("emoji")
                                label = mapping.get("label")
                                style_str = mapping.get("style", "secondary").lower()
                                style = self.CLASS_STYLE_MAP.get(style_str, discord.ButtonStyle.secondary)
                                current_row.add_item(ReactionRoleButton(role_id=role_id, label=label, emoji=emoji, style=style))
                            if len(current_row.children) > 0:
                                container.add_item(current_row)
                        
                        image = config_data.get("image")
                        if image:
                            container.add_item(Separator(visible=False))
                            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(image)))
                        view.add_item(container)
                    except ImportError: pass
                        
                    message = await channel.send(view=view)
                    await self.db.save_reaction_role_message(guild.id, identifier, channel.id, message.id)

                    if mode == "reactions":
                        for mapping in mappings:
                            emoji_str = mapping.get("emoji")
                            if emoji_str:
                                custom_match = re.search(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>', emoji_str)
                                if custom_match:
                                    emoji_obj = self.bot.get_emoji(int(custom_match.group(1)))
                                    if emoji_obj: await message.add_reaction(emoji_obj)
                                    else: await message.add_reaction(emoji_str)
                                else: await message.add_reaction(emoji_str)
            except Exception as e:
                log.error(f"Error processing reaction role {idx}: {e}", exc_info=True)

    async def _handle_reaction(self, payload, add_role: bool):
        if not payload.guild_id: return
        if payload.member and payload.member.bot: return
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        member = payload.member or guild.get_member(payload.user_id)
        if not member or member.bot: return

        matched_mapping = None
        for idx, config_data in enumerate(Config.REACTION_ROLES):
            if config_data.get("enabled", True) is False: continue
            identifier = config_data.get("identifier", f"rr_menu_{idx}")
            db_record = await self.db.get_reaction_role_message(payload.guild_id, identifier)
            if db_record and db_record[1] == payload.message_id:
                for mapping in config_data.get("mappings", []):
                    map_emoji = mapping.get("emoji")
                    if not map_emoji: continue
                    is_match = False
                    if payload.emoji.is_custom_emoji():
                        if str(payload.emoji.id) in map_emoji: is_match = True
                    else:
                        if payload.emoji.name == map_emoji: is_match = True
                    if is_match:
                        matched_mapping = mapping
                        break
            if matched_mapping: break
                
        if matched_mapping:
            role_id = matched_mapping.get("role_id")
            if not role_id: return
            role = guild.get_role(role_id)
            if role:
                try:
                    if add_role:
                        if role not in member.roles:
                            await member.add_roles(role)
                            log.info(f"ReactionRole: Added {role.name} to {member.display_name}")
                    else:
                        if role in member.roles:
                            await member.remove_roles(role)
                            log.info(f"ReactionRole: Removed {role.name} from {member.display_name}")
                except discord.Forbidden:
                    log.warning(f"Forbidden: Could not manage role {role.name} for {member.display_name}. Check bot position hierarchy.")
                except Exception as e:
                    log.error(f"Error managing reaction role: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        await self._handle_reaction(payload, add_role=True)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        await self._handle_reaction(payload, add_role=False)

async def setup(bot):
    await bot.add_cog(ReactionRolesCog(bot))
