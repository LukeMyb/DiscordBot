import discord
from discord.ext import commands
import aiosqlite

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None

    async def cog_load(self): # 非同期処理の初期化
        await self.init_db()

    async def init_db(self): # データベースの初期化
        # ランキング機能専用のデータベースを分離して作成
        self.db = await aiosqlite.connect("data/ranking.db")
        
        # 送信先チャンネルを保存するsettingsテーブルを作成
        # サーバーごとに1つの設定を持たせるため、guild_idを主キー(PRIMARY KEY)に設定します
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        await self.db.commit()

async def setup(bot):
    await bot.add_cog(Ranking(bot))