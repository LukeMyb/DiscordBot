import discord
from discord.ext import commands

class VcPredictor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

async def setup(bot):
    await bot.add_cog(VcPredictor(bot))