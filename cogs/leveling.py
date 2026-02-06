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
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def sync_show_levels(self, ctx): #管理者がギルド全員のレベルを名前の横に表示(更新)する
        for member in ctx.guild.members:
            if member.bot: continue

            fetch = await self.db.execute("""
                SELECT msg_count FROM levels WHERE user_id = ?
            """, (member.id, ))
            fetch = await fetch.fetchone() #クエリを取り出す
            msg_count: int = 0
            if fetch != None:
                msg_count = fetch[0] #クエリを数値に変換

            level: int = 1
            temp: int = msg_count
            while level * 10 <= temp: #Lv.1:0~9, Lv.2:10~29, Lv.3:30~59, ... (LvUPする度に必要メッセージ数が10ずつ増えていく)
                temp -= level * 10
                level += 1
            
            try:
                await member.edit(nick=f"[Lv.{level}] {member.global_name}") #レベルを更新
            except discord.Forbidden: #ニックネーム変更権限がない, または階層が上の場合はスルー
                pass
            except Exception as e:
                await ctx.send(content=f"{e}")

    @commands.Cog.listener()
    async def on_message(self, message): #レベルの動的更新
        if message.author.bot: return

        #メッセージを受け取ったらメッセージ数+1
        await self.db.execute("""
            INSERT INTO levels (user_id, msg_count)
            VALUES (?, 1)
            ON CONFLICT(user_id) DO UPDATE SET
                msg_count = levels.msg_count + 1
        """, (message.author.id, ))

        await self.db.commit()

        #レベルが上がったらレベル表示を更新
        fetch = await self.db.execute("""
            SELECT msg_count FROM levels WHERE user_id = ?
        """, (message.author.id, ))
        fetch = await fetch.fetchone() #クエリを取り出す
        msg_count: int = 0
        if fetch != None:
            msg_count = fetch[0] #クエリを数値に変換

        level: int = 1
        temp: int = msg_count
        while level * 10 <= temp: #Lv.1:0~9, Lv.2:10~29, Lv.3:30~59, ... (LvUPする度に必要メッセージ数が10ずつ増えていく)
            temp -= level * 10
            level += 1

        pre_level: int = 1
        temp = msg_count - 1
        while pre_level * 10 <= temp:
            temp -= pre_level * 10
            pre_level += 1
        
        if pre_level != level or "[Lv." not in message.author.display_name: #メッセージ送信前と後のレベルを比較してレベルアップを検知
            try:
                await message.author.edit(nick=f"[Lv.{level}] {message.author.global_name}") #レベルを更新
            except discord.Forbidden: #ニックネーム変更権限がない, または階層が上の場合はスルー
                pass
            except Exception as e:
                await message.channel.send(content=f"{e}")

async def setup(bot):
    await bot.add_cog(Leveling(bot))