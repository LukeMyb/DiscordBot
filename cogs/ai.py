import discord
from discord.ext import commands

class Ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def get_conv(self, ctx): #学習データを抽出
        status_msg = await ctx.send("会話データの取得を開始します。時間がかかる場合があります...")
        count: int = 0
        data: list = []
        for channel in ctx.guild.text_channels: #全チャンネルを探索
            try:
                async for message in channel.history(limit=None): #チャンネル内の全メッセージを探索
                    if message.author.bot: continue #botならスルー
                    data.append(message.content)

                    if len(data) == 1000: #リストのメッセージ数が100を超えたら一旦テキストファイルに保存
                        with open("conv_data.txt", "a", encoding="utf-8") as file:
                            file.write("\n".join(data) + "\n")
                            count += 1000
                            data = []

                        await status_msg.edit(content=f"取得したメッセージ数: {count}")
                    
                if len(data) != 0:
                    with open("conv_data.txt", "a", encoding="utf-8") as file:
                        file.write("\n".join(data) + "\n")
                        count += len(data)
                        data = []

                    await status_msg.edit(content=f"取得したメッセージ数: {count}")
            except discord.Forbidden:
                pass
            except Exception as e:
                print(e)

        await status_msg.edit(content=f"探索が終了しました\n取得したメッセージ数: {count}")

async def setup(bot):
    await bot.add_cog(Ai(bot))