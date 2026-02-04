import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #キック
    @commands.command()
    @commands.has_permissions(kick_members=True) #実行者の権限確認
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} をキックしました。理由: {reason}")

    #BAN
    @commands.command()
    @commands.has_permissions(ban_members=True) #実行者の権限確認
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} をBANしました。理由: {reason}")

async def setup(bot):
    await bot.add_cog(Admin(bot))