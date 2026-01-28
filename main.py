import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

class MyBot(commands.Bot):
    def __init__(self):
        # 必要なインテント（権限）の設定
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix="!",
            intents=intents
        )

    async def setup_hook(self):
        # ここでcogsフォルダ内のファイルを読み込む処理を書く
        # 最初はシンプルに起動確認のみ
        print(f"Logged in as {self.user}")

load_dotenv() #.envの内容を環境変数としてロード
bot = MyBot()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)