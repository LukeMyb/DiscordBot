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

        # 絵文字の名前が「bad_social_credit」でない場合は処理を終了する
        if payload.emoji.name != "bad_social_credit":
            return

        channel = self.bot.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            # ペイロードからメッセージオブジェクトを取得
            message = await channel.fetch_message(payload.message_id)
        except (discord.NotFound, discord.Forbidden):
            return
        
        # 既にBotが📌を付けている場合は処理を終了する（重複防止）
        for reaction in message.reactions:
            if str(reaction.emoji) == "📌" and reaction.me:
                return

        # 追加されたリアクションのカウントを確認する
        for reaction in message.reactions:
            # 文字列に変換して絵文字が一致するか判定する
            if str(reaction.emoji) == str(payload.emoji):
                # リアクションが2つついた時にメッセージを返信する
                if reaction.count == 2:
                    await message.add_reaction("📌")

                    # 「ピンボード」という名前のチャンネルを探索
                    target_channel = discord.utils.get(message.guild.text_channels, name="ピンボード")
                    if target_channel:
                        # Embedの作成
                        embed = discord.Embed(
                            description=message.content, # メッセージ本文
                            color=0xFFD700, # ゴールド系の色
                            timestamp=message.created_at # 元のメッセージの投稿時間
                        )
                        # 投稿者の名前とアイコンを設定
                        embed.set_author(
                            name=message.author.display_name,
                            icon_url=message.author.display_avatar.url
                        )

                        # contentとembedを同時に送信する
                        await target_channel.send(
                            content=f"{payload.emoji} {reaction.count} | {message.jump_url}",
                            embed=embed
                        )
                break

async def setup(bot):
    await bot.add_cog(Pinboard(bot))