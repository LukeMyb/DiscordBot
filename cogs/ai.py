import discord
from discord.ext import commands
import re

class Ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clean_text(self, text):
        text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-@]+', '', text) #URLを削除
        text = re.sub(r'<[@#&]!?\d+>', '', text) #メンション・チャンネルリンクを削除
        text = re.sub(r'@everyone|@here', '', text) #@everyoneと@hereを削除
        text = re.sub(r'@\S+', '', text) #@から始まる単語(SNSハンドルやURLの残骸)を削除
        text = re.sub(r'<a?:\w+:\d+>', '', text) #カスタム絵文字を削除
        text = re.sub(r'\n+', '\n', text) #連続する改行を1つの改行に変換
        return text.strip() #前後の余計な空白を消して, 中身があれば返す

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def get_conv(self, ctx): #学習データを抽出
        status_msg = await ctx.send("会話データの取得を開始します。時間がかかる場合があります...")
        count: int = 0
        data: list = []
        for channel in ctx.guild.text_channels: #全チャンネルを探索
            if channel.id in [1280150783161143297, 1280292202949644369, 1317465310403624990]: continue #通話募集用のチャンネルなどは学習データに含めない

            try:
                async for message in channel.history(limit=None, oldest_first=True): #チャンネル内の全メッセージを探索
                    if message.author.bot: continue #botならスルー
                    cleaned: str = self.clean_text(message.content)
                    if cleaned: #中身が空っぽでなければlistに追加
                        data.append(cleaned)

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