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

        #入室・退室・移動の判定
        if before.channel is None and after.channel is not None: #新しくVCに参加した場合
            msg = f"ID: {member.id}, JOIN | **{member.display_name}** が '{after.channel.name}' に参加しました。"
        elif before.channel is not None and after.channel is None: #VCから完全に退出した場合
            msg = f"ID: {member.id}, LEAVE | **{member.display_name}** が '{before.channel.name}' から退出しました。"
        elif before.channel is not None and after.channel is not None: #VC間を移動した場合
            msg = f"ID: {member.id}, MOVE | **{member.display_name}** が '{before.channel.name}' → '{after.channel.name}' へ移動しました。"
        else:
            return

        await log_channel.send(msg)

async def setup(bot):
    await bot.add_cog(Log(bot))