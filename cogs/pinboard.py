import discord
from discord.ext import commands

class Pinboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        # Bot自身のリアクションは除外する
        if payload.member and payload.member.bot:
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            # ペイロードからメッセージオブジェクトを取得
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        # 追加されたリアクションのカウントを確認する
        for reaction in message.reactions:
            # 文字列に変換して絵文字が一致するか判定する
            if str(reaction.emoji) == str(payload.emoji):
                # リアクションが2つついた時にメッセージを返信する
                if reaction.count == 2:
                    await message.reply(content="リアクションが2つ付きました")
                break

async def setup(bot):
    await bot.add_cog(Pinboard(bot))