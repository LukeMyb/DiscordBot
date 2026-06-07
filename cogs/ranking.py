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

    # 送信先チャンネルを設定するコマンド
    @commands.command(name="set_ranking_channel")
    @commands.has_permissions(administrator=True) # 管理者権限を要求
    async def set_ranking_channel(self, ctx, channel: discord.TextChannel = None):
        # 引数が指定された場合はそのチャンネルを、省略された場合は現在のチャンネルを使用
        target_channel = channel or ctx.channel

        # INSERT OR REPLACE を使用して、新規登録と上書き更新を安全に処理する
        await self.db.execute("""
            INSERT OR REPLACE INTO settings (guild_id, channel_id)
            VALUES (?, ?)
        """, (ctx.guild.id, target_channel.id))
        await self.db.commit()
        
        await ctx.send(f"{target_channel.mention} を月間ランキングの発表先に設定しました")

async def setup(bot):
    await bot.add_cog(Ranking(bot))