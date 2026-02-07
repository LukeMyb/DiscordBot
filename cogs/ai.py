import discord
from discord.ext import commands
import os
import re #正規表現を扱う (特定のルール(パターン)に基づいた文字の塊を見つけ出し, 自由自在に加工する)
import csv
from janome.tokenizer import Tokenizer #品詞分解
from datetime import datetime

class Ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def clean_text(self, text: str): #学習時にノイズとなる文字列を削除
        text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-@]+', '', text) #URLを削除
        text = re.sub(r'<[@#&]!?\d+>', '', text) #メンション・チャンネルリンクを削除
        text = re.sub(r'@everyone|@here', '', text) #@everyoneと@hereを削除
        text = re.sub(r'@\S+', '', text) #@から始まる単語(SNSハンドルやURLの残骸)を削除
        text = re.sub(r'<a?:\w+:\d+>', '', text) #カスタム絵文字を削除
        text = re.sub(r'\n+', '\n', text) #連続する改行を1つの改行に変換
        return text.strip() #前後の余計な空白を消して, 中身があれば返す
    
    def write2csv(self, data: list):
        with open("conv_data.csv", "a", encoding="utf-8-sig", newline="") as file: #newline=""は改行コードの自動変換をしないように, -sigはexcelで文字化けしなくなるらしい
            writer = csv.writer(file)
            writer.writerows(data)

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def get_conv(self, ctx): #学習データを抽出
        if not os.path.exists("conv_data.csv"): #csvファイルが無かったらヘッダーをつけて作成
            self.write2csv([["timestamp", "user_id", "message_content"]])

        status_msg = await ctx.send("会話データの取得を開始します。時間がかかる場合があります...")
        count: int = 0 #取得したメッセージ数
        data: list = [] #csvに書き込む前に一時的にリストに保存
        for channel in ctx.guild.text_channels: #全チャンネルを探索
            if channel.id in [1280150783161143297, 1280292202949644369, 1317465310403624990]: continue #通話募集用のチャンネルなどは学習データに含めない

            try:
                async for message in channel.history(limit=None, oldest_first=True): #チャンネル内の全メッセージを探索
                    if message.author.bot: continue #botならスルー
                    cleaned: str = self.clean_text(message.content)
                    if cleaned: #中身が空っぽでなければlistに追加
                        data.append([str(message.created_at), str(message.author.id), cleaned]) #送信時刻, ユーザーid, クレンジングしたメッセージを格納

                    if len(data) == 1000: #リストのメッセージ数が1000を超えたら一旦ファイルに保存
                        self.write2csv(data)
                        count += 1000
                        data = []

                        await status_msg.edit(content=f"取得したメッセージ数: {count}")
                    
                if len(data) != 0:
                    self.write2csv(data)
                    count += len(data)
                    data = []

                    await status_msg.edit(content=f"取得したメッセージ数: {count}")
            except discord.Forbidden:
                pass
            except Exception as e:
                print(e)

        await status_msg.edit(content=f"探索が終了しました\n取得したメッセージ数: {count}")

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def part_of_speech(self, ctx): #品詞分解
        with open("conv_data.csv", encoding="utf-8-sig") as file:
            t = Tokenizer()
            reader = csv.reader(file)
            data: list = [] #[時刻, ユーザーid, 文章を品詞分解した単語のリスト]
            next(reader) #ヘッダーを除外
            for row in reader: #csvの形は timestamp, user id, message content
                tokens = t.tokenize(row[2]) #品詞分解(この時点では品詞などの情報も含まれるオブジェクト)
                
                #品詞などの情報を除外
                token_surface: list = []
                for token in tokens:
                    token_surface.append(token.surface)

                data.append([datetime.fromisoformat(row[0]), row[1], token_surface])

async def setup(bot):
    await bot.add_cog(Ai(bot))