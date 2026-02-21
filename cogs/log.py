import discord
from discord.ext import commands

class Log(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.deployed_bot_id = 1472722426155630622 #デプロイした方のコードを動かすボットのユーザーid

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.bot.user: return #ボットの準備が完了していない場合は無視
        if self.bot.user.id != self.deployed_bot_id: return #デプロイした方を動かすボットかどうか

        log_channel = discord.utils.get(member.guild.text_channels, name="log") #「log」というチャンネル名のチャンネルを検索
        if not log_channel: return

        embed = discord.Embed() #embedの初期化

        #入室・退室・移動の判定
        if before.channel is None and after.channel is not None: #新しくVCに参加した場合
            embed.color = discord.Color.green() #入室は緑色
            embed.title = "JOIN"
            embed.description = f"**{member.display_name}** が '{after.channel.name}' に参加しました。"
            embed.set_footer(text=f"ID: {member.id} | ACTION: JOIN")

        elif before.channel is not None and after.channel is None: #VCから完全に退出した場合
            embed.color = discord.Color.red() #退室は赤色
            embed.title = "LEAVE"
            embed.description = f"**{member.display_name}** が '{before.channel.name}' から退出しました。"
            embed.set_footer(text=f"ID: {member.id} | ACTION: LEAVE")

        elif before.channel is not None and after.channel is not None: #VC間を移動した場合
            embed.color = discord.Color.blue() #移動は青色
            embed.title = "MOVE"
            embed.description = f"**{member.display_name}** が '{before.channel.name}' → '{after.channel.name}' へ移動しました。"
            embed.set_footer(text=f"ID: {member.id} | ACTION: MOVE")

        else:
            return

        await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Log(bot))