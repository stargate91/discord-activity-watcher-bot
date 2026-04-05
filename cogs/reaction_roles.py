import discord
from discord.ext import commands
from core.logger import log
from config_loader import Config
import re

class ReactionRolesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    async def cog_load(self):
        # Start the background initialization task
        self.bot.loop.create_task(self.init_reaction_roles())

    async def init_reaction_roles(self):
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
                        # Auto-resolve missing role IDs via name
                        if mapping.get("role_id", 0) == 0 and mapping.get("role_name"):
                            role = discord.utils.get(guild.roles, name=mapping.get("role_name"))
                            if role:
                                mapping["role_id"] = role.id
                                
                        # Auto-resolve missing emojis via name
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
                    except discord.NotFound:
                        log.error(f"Channel {channel_id} is completely deleted/unreachable.")
                        continue
                    except discord.Forbidden:
                        log.error(f"Channel {channel_id} is forbidden.")
                        continue
                        
                bot_name = guild.me.display_name if guild else self.bot.user.name

                # Check DB to see if we already sent this message
                db_record = self.db.get_reaction_role_message(identifier)
                message = None

                if db_record:
                    saved_channel_id, saved_message_id = db_record
                    if saved_channel_id == channel_id:
                        try:
                            message = await channel.fetch_message(saved_message_id)
                        except discord.NotFound:
                            # Message was deleted from discord
                            pass
                        except discord.Forbidden:
                            log.error(f"Cannot read message history in {channel.name}")

                # If we don't have the message, we need to send a new one
                if message is None:
                    log.info(f"Sending new reaction role message for {identifier}")

                    view = discord.ui.View() # Fallback for now if LayoutView not in main discord
                    try:
                        from discord.ui import LayoutView, Container, Section, TextDisplay, Thumbnail, Separator, MediaGallery
                        view = LayoutView()
                        container = Container(accent_color=discord.Color.from_str(config_data.get("color", "0x5865F2")))
                        
                        title = config_data.get("title", "Szerepkörök")
                        if title: title = title.replace("{bot_name}", bot_name)

                        desc = config_data.get("description", "Válaszd ki a szerepeidet!")
                        if desc: desc = desc.replace("{bot_name}", bot_name)
                        
                        content_text = f"## {title}\n{desc}"
                        container.add_item(TextDisplay(content_text))
                        
                        mappings = config_data.get("mappings", [])
                        
                        if mappings:
                            container.add_item(Separator(visible=False))
                            lines = []
                            for mapping in mappings:
                                emoji = mapping.get("emoji")
                                label = mapping.get("label", "")
                                if emoji:
                                    lines.append(f"{emoji} **{label}**")
                            if lines:
                                container.add_item(TextDisplay(">>> " + "\\n".join(lines)))
                        
                        image = config_data.get("image")
                        if image:
                            container.add_item(Separator(visible=False))
                            # Fallback to TextDisplay if MediaGallery doesn't accept url directly or we use discord.MediaGalleryItem
                            container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(image)))

                        view.add_item(container)
                    except ImportError:
                        pass # if discord.ui doesn't have LayoutView
                        
                    message = await channel.send(view=view)
                    
                    # Save to DB
                    self.db.save_reaction_role_message(identifier, channel.id, message.id)

                    # Add emojis
                    for mapping in mappings:
                        emoji_str = mapping.get("emoji")
                        if emoji_str:
                            # Try to resolve custom emoji strings
                            custom_match = re.search(r'<a?:[a-zA-Z0-9_]+:([0-9]+)>', emoji_str)
                            if custom_match:
                                emoji_obj = self.bot.get_emoji(int(custom_match.group(1)))
                                if emoji_obj:
                                    await message.add_reaction(emoji_obj)
                                else:
                                    await message.add_reaction(emoji_str) # Discord might still accept the string if it's external
                            else:
                                await message.add_reaction(emoji_str) # unicode
            except Exception as e:
                log.error(f"Error processing reaction role {idx}: {e}", exc_info=True)

    async def _handle_reaction(self, payload, add_role: bool):
        # We only care about our configured guilds
        if payload.guild_id != Config.GUILD_ID:
            return

        if payload.member and payload.member.bot:
            return # Ignore bot reactions
            
        guild = self.bot.get_guild(payload.guild_id)
        if not guild: return
        
        # We need member object. For remove, payload.member is None.
        member = payload.member or guild.get_member(payload.user_id)
        if not member or member.bot: return

        # Is this message part of our reaction roles?
        matched_mapping = None
        for idx, config_data in enumerate(Config.REACTION_ROLES):
            if config_data.get("enabled", True) is False:
                continue
                
            identifier = config_data.get("identifier", f"rr_menu_{idx}")
            db_record = self.db.get_reaction_role_message(identifier)
            if db_record and db_record[1] == payload.message_id:
                # This is a reaction role message! Let's check the emoji
                for mapping in config_data.get("mappings", []):
                    map_emoji = mapping.get("emoji")
                    if not map_emoji: continue
                    
                    # Check if string matches. Payload emoji can be unicode or partial custom string
                    is_match = False
                    if payload.emoji.is_custom_emoji():
                        if str(payload.emoji.id) in map_emoji:
                            is_match = True
                    else:
                        if payload.emoji.name == map_emoji:
                            is_match = True
                            
                    if is_match:
                        matched_mapping = mapping
                        break
            
            if matched_mapping:
                break
                
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
