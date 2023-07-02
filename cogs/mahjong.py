import discord

from discord.ext import commands
from utility.func import getLogger
 	
logger = getLogger(__name__)


class Mahjong(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
 	
    @commands.command(name="test")
    async def tester(self, ctx):
        await ctx.send("HELLO")

async def setup(bot):
    await bot.add_cog(Mahjong(bot))