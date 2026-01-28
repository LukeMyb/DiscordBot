# cogs/ping.py
import discord
from discord.ext import commands

# 親クラス commands.Cog を継承する
class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # コマンドを定義するデコレータ
    @commands.command()
    async def ping(self, ctx):
        # ctx は "Context"（文脈）の略。送信者やチャンネルの情報が詰まっている
        await ctx.send("pong")

# main.py からこのファイルを読み込むための関数
async def setup(bot):
    await bot.add_cog(Ping(bot))