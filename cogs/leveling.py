import discord
from discord.ext import commands
import aiosqlite #非同期処理に対応したSQL
import asyncio

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None

    async def cog_load(self): #非同期処理の初期化
        await self.init_db()

    async def init_db(self): #データベースの初期化
        self.db = await aiosqlite.connect("data/leveling.db")
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                guild_id INTEGER,
                user_id INTEGER,
                msg_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (guild_id, user_id) --この2つの組み合わせを唯一の鍵にする
            )
        """)
        await self.db.commit()

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def sync_levels(self, ctx): #管理者がギルド全員のレベルを同期させる
        status_msg = await ctx.send("同期を開始します。時間がかかる場合があります...")
        counts: dict = {}
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
                INSERT INTO levels (guild_id, user_id, msg_count) --データを格納
                VALUES (?, ?, ?) --?はSQLインジェクションを防ぐため
                ON CONFLICT(guild_id, user_id) DO UPDATE SET --user_idが既にあってエラーが起きたら(CONFLICT)更新(UPDATE)に切り替える
                    msg_count = excluded.msg_count --既存のmsg_countを, 本来入れるはずだった新しい値(excluded.msg_count)で書き換える
            """, (ctx.guild.id, user_id, msg_count))

        await self.db.commit()
        await status_msg.edit(content="同期が完了しました")

    def get_level(self, msg_count):
        level: int = 1
        temp: int = msg_count
        while level * 10 <= temp: #Lv.1:0~9, Lv.2:10~29, Lv.3:30~59, ... (LvUPする度に必要メッセージ数が10ずつ増えていく)
            temp -= level * 10
            level += 1

        return level, temp #tempはlevel*10の端数

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def sync_show_levels(self, ctx): #管理者がギルド全員のレベルを名前の横に表示(更新)する
        status_msg = await ctx.send(content="全メンバーのレベルとロールを同期しています...")
        for member in ctx.guild.members:
            if member.bot: continue

            fetch = await self.db.execute("""
                SELECT msg_count FROM levels WHERE user_id = ? AND guild_id = ?
            """, (member.id, ctx.guild.id))
            fetch = await fetch.fetchone() #クエリを取り出す
            msg_count: int = 0
            if fetch != None:
                msg_count = fetch[0] #クエリを数値に変換

            level, temp = self.get_level(msg_count)
            try:
                await member.edit(nick=f"[Lv.{level}] {member.global_name or member.name}") #レベルを更新

                # 現在のレベルに基づく適切なロールの計算と一斉付与・剥奪
                # 例: Lv34なら30、Lv8なら0、Lv55なら50になるよう計算
                target_role_level = min((level // 10) * 10, 50)

                # 10〜50の全レベルロールを確認し、正しいものだけ残して他は消す（クレンジング）
                for r_level in [10, 20, 30, 40, 50]:
                    role = discord.utils.get(ctx.guild.roles, name=f"Lv.{r_level}")
                    if not role: continue
                    
                    if r_level == target_role_level:
                        # 本来持つべきロールを持っていない場合のみ付与
                        if role not in member.roles:
                            await member.add_roles(role)
                    else:
                        # 持つべきではない過去・未来のロールを持っていたら剥奪
                        if role in member.roles:
                            await member.remove_roles(role)

                await asyncio.sleep(1)
            except discord.Forbidden: #ニックネーム変更権限がない, または階層が上の場合はスルー
                pass
            except Exception as e:
                await ctx.send(content=f"{e}")
        
        await status_msg.edit(content="全メンバーのレベルとロールの同期が完了しました")

    @commands.Cog.listener()
    async def on_message(self, message): #レベルの動的更新
        if message.author.bot or message.guild is None: return

        #メッセージを受け取ったらメッセージ数+1
        await self.db.execute("""
            INSERT INTO levels (guild_id, user_id, msg_count)
            VALUES (?, ?, 1)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET
                msg_count = levels.msg_count + 1
        """, (message.guild.id, message.author.id, ))

        await self.db.commit()

        #レベルが上がったらレベル表示を更新
        fetch = await self.db.execute("""
            SELECT msg_count FROM levels WHERE user_id = ? AND guild_id = ?
        """, (message.author.id, message.guild.id))
        fetch = await fetch.fetchone() #クエリを取り出す
        msg_count: int = 0
        if fetch != None:
            msg_count = fetch[0] #クエリを数値に変換
        
        level, temp = self.get_level(msg_count)
        pre_level, temp = self.get_level(msg_count-1)
        if pre_level != level or "[Lv." not in message.author.display_name: #メッセージ送信前と後のレベルを比較してレベルアップを検知
            try:
                await message.author.edit(nick=f"[Lv.{level}] {message.author.global_name or message.author.name}") #レベルを更新

                #名前修復時ではなく, 純粋にレベルが上がった時だけリアクションを付与する
                if pre_level != level:
                    await message.add_reaction("🎉")

                    #レベルが10の倍数(10, 20...)の時にロールを付与・切り替え
                    if level % 10 == 0:
                        #付与する新しいロールを名前で検索
                        new_role = discord.utils.get(message.guild.roles, name=f"Lv.{level}")
                        if new_role:
                            await message.author.add_roles(new_role)

                        #1つ前の階級のロールがあれば剥奪する（ロール欄が被らないように綺麗に保つ）
                        if level >= 20:
                            old_role = discord.utils.get(message.guild.roles, name=f"Lv.{level-10}")
                            if old_role and old_role in message.author.roles:
                                await message.author.remove_roles(old_role)
            except discord.Forbidden: #ニックネーム変更権限がない, または階層が上の場合はスルー
                pass

            
            except Exception as e:
                await message.channel.send(content=f"{e}")

    @commands.command()
    async def level(self, ctx, target: discord.Member = None): #現在のレベルとプログレスを表示
        #targetが指定されていない場合はコマンド実行者(ctx.author)を対象にする
        target = target or ctx.author

        fetch = await self.db.execute("""
            SELECT msg_count FROM levels WHERE user_id = ? AND guild_id = ?
        """, (target.id, ctx.guild.id))
        fetch = await fetch.fetchone() #クエリを取り出す
        msg_count: int = 0
        if fetch != None:
            msg_count = fetch[0] #クエリを数値に変換

        embed = discord.Embed(title=f"現在の{target.global_name or target.name}のレベル", color=0x0000FF)
        embed.set_thumbnail(url=target.display_avatar.url)
        level, temp = self.get_level(msg_count)
        embed.add_field(name=f"[Lv.{level}] {target.global_name or target.name} ({target.name})", value=f"`|{'█' * (temp*20//(level*10))}{'░' * (20 - temp*20//(level*10))}| {temp*100//(level*10)}% Lv.{level+1}まであと{level*10 - temp}`", inline = False) #プログレスバーと次のレベルまで必要なメッセージ数の表示
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))