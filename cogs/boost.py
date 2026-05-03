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
            
        if before.premium_since is None and after.premium_since is not None:
            await self.handle_boost(after)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        pass

    async def handle_boost(self, member: discord.Member):
        from core.notifications import NotificationService
        await NotificationService.send_notification(member, Config.BOOST)

async def setup(bot):
    await bot.add_cog(BoostCog(bot))

