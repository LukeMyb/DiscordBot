import discord
from discord.ext import commands
import aiosqlite

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.init_db(self)

    async def init_db(self):
        self.db = await aiosqlite.connect("leveling.db")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER NOT NULL,
                level INTEGER NOT NULL
            )
        """)
        await self.db.commit()

    @commands.command()
    async def level(self, ctx):
        await ctx.send("This is a leveling command.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))