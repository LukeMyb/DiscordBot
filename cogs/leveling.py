import discord
from discord.ext import commands
import aiosqlite

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None

    async def cog_load(self): #非同期処理の初期化
        await self.init_db()

    async def init_db(self): #データベースの初期化
        self.db = await aiosqlite.connect("leveling.db")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                user_id INTEGER PRIMARY KEY,
                msg_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await self.db.commit()

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def sync_levels(self, ctx): #管理者がギルド全員のレベルを同期させる
        status_msg = await ctx.send("同期を開始します。時間がかかる場合があります...")
        counts = {}
        for channel in ctx.guild.text_channels: #全チャンネルを探索
            await status_msg.edit(content=f"{channel.mention}を探索中...")

            try:
                async for message in channel.history(limit=None): #チャンネル内の全メッセージを探索
                    if message.author.bot: continue #botならスルー
                    counts[message.author.id] = counts.get(message.author.id, 0) + 1 #get(A, B)はAがcountsに無かったらBの値で初期化
            except discord.Forbidden:
                pass
            except Exception as e:
                await status_msg.edit(content=f"{e}")

        await status_msg.edit(content="データベースに保存中...")

        for user_id, msg_count in counts.items():
            await self.db.execute("""
                INSERT INTO levels (user_id, msg_count) --データを格納
                VALUES (?, ?) --?はSQLインジェクションを防ぐため
                ON CONFLICT(user_id) DO UPDATE SET --user_idが既にあってエラーが起きたら(CONFLICT)更新(UPDATE)に切り替える
                    msg_count = excluded.msg_count --既存のmsg_countを, 本来入れるはずだった新しい値(excluded.msg_count)で書き換える
            """, (user_id, msg_count))

        await self.db.commit()
        await status_msg.edit(content="同期が完了しました")
            

    @commands.command()
    async def level(self, ctx):
        await ctx.send("This is a leveling command.")

async def setup(bot):
    await bot.add_cog(Leveling(bot))