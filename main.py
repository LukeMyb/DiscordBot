import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

class MyBot(commands.Bot): #commands.botは継承元である親クラス
    def __init__(self): #コンストラクタ #selfはインスタンス化したときのそのインスタンスを表す
        intents = discord.Intents.default() #必要なインテント(権限)の設定, 一般的によく使われる標準的なイベント通知を受け取る(メッセージ本文などの機密情報はデフォルト設定では取得できない)
        intents.members = True
        intents.message_content = True #メッセージ本文を読み取る権限を有効にする
        
        super().__init__( #親クラス(スーパークラス)のコンストラクタ, Pythonでは親クラスも明示的に初期化してあげる必要がある, selfが無くても自動で親クラスのメソッドにインスタンスを引き渡してくれる
            command_prefix="!", #コマンドの接頭辞
            intents=intents #intentsオブジェクトを親クラスに渡す
        )

    async def setup_hook(self): #非同期のネットワークが絡む初期設定
        await self.load_extension("cogs.ping")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.leveling")
        print(f"Logged in as {self.user}")

load_dotenv() #.envの内容を環境変数としてロード
bot = MyBot()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)