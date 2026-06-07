import discord
from discord.ext import commands, tasks
import aiosqlite
import datetime
import zoneinfo

class Ranking(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = None
        self.jst = zoneinfo.ZoneInfo("Asia/Tokyo") # 日本時間の設定

    async def cog_load(self): # 非同期処理の初期化
        await self.init_db()
        self.monthly_ranking_task.start() # コグのロード時にタスクを開始

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
        

    # コアロジック（指定期間のメッセージを集計し、上位5名を取得）
    async def get_monthly_ranking(self, guild: discord.Guild):
        now = datetime.datetime.now(self.jst)
        
        # 今月1日と先月1日の0時0分を計算
        this_month_first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if this_month_first.month == 1:
            last_month_first = this_month_first.replace(year=this_month_first.year - 1, month=12)
        else:
            last_month_first = this_month_first.replace(month=this_month_first.month - 1)
            
        message_counts = {}

        # サーバー内の全テキストチャンネルをスキャン
        for channel in guild.text_channels:
            try:
                # 権限がないチャンネルでのエラーを回避するため try-except を使用
                async for message in channel.history(after=last_month_first, before=this_month_first, limit=None):
                    # Bot自身の発言は集計から除外
                    if message.author.bot:
                        continue
                    
                    user_id = message.author.id
                    message_counts[user_id] = message_counts.get(user_id, 0) + 1
            except discord.Forbidden:
                continue
        
        # 辞書を値（メッセージ数）で降順にソートし、上位5名を取得
        sorted_ranking = sorted(message_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return sorted_ranking, last_month_first.month
    
    
    # 毎月1日の深夜1時に実行されるタスク
    # JSTの深夜1時をタイムゾーン付きで指定
    target_time = datetime.time(hour=1, minute=0, tzinfo=zoneinfo.ZoneInfo("Asia/Tokyo"))
    
    @tasks.loop(time=target_time)
    async def monthly_ranking_task(self):
        now = datetime.datetime.now(self.jst)
        
        # 今日が「1日」ではない場合は処理をスキップ
        if now.day != 1:
            return

        # データベースから設定が登録されている全てのサーバーとチャンネルを取得
        async with self.db.execute("SELECT guild_id, channel_id FROM settings") as cursor:
            rows = await cursor.fetchall()
        
        for guild_id, channel_id in rows:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue # Botがサーバーからキックされている場合などの安全策
            
            target_channel = guild.get_channel(channel_id)
            if not target_channel:
                continue # チャンネルが削除されている場合などの安全策
            
            # 集計処理とEmbed作成
            ranking_data, target_month = await self.get_monthly_ranking(guild)
            
            # 誰一人として発言していない月は送信をスキップ（不要な通知を防ぐため）
            if not ranking_data:
                continue

            embed = discord.Embed(
                title=f"👑 {target_month}月 メッセージ送信数ランキング",
                description="先月最もサーバーを盛り上げてくれたメンバーです！",
                color=0x00BFFF
            )
            
            medals = ["🥇", "🥈", "🥉", " ", " "]
            for i, (user_id, count) in enumerate(ranking_data):
                member = guild.get_member(user_id)
                name = member.display_name if member else "不明なユーザー"
                
                embed.add_field(
                    name=f"{medals[i]} 第{i+1}位: {name}",
                    value=f"{count} メッセージ",
                    inline=False
                )

            await target_channel.send(embed=embed)

    @monthly_ranking_task.before_loop
    async def before_monthly_ranking_task(self):
        # Botの内部キャッシュの準備が完了するまでタスクの実行を待機
        await self.bot.wait_until_ready()


    # 手動確認用コマンド
    @commands.command(name="ranking")
    async def show_ranking(self, ctx):
        # データベースから設定されたチャンネルIDを取得
        async with self.db.execute("SELECT channel_id FROM settings WHERE guild_id = ?", (ctx.guild.id,)) as cursor:
            row = await cursor.fetchone()
        
        # 設定が存在しない場合の処理
        if not row:
            await ctx.send("ランキングの送信先チャンネルが設定されていません。先に `!set_ranking_channel` で設定してください。")
            return
            
        # チャンネルオブジェクトの取得と存在確認
        target_channel = self.bot.get_channel(row[0])
        if not target_channel:
            await ctx.send("設定されたチャンネルが見つかりません。再設定を行ってください。")
            return

        # 処理に時間がかかる可能性があるため、入力中(typing)のアクションを表示
        async with ctx.typing():
            ranking_data, target_month = await self.get_monthly_ranking(ctx.guild)
            
            if not ranking_data:
                await target_channel.send(f"{target_month}月のメッセージデータが見つかりませんでした。")
                return

            # Embedの作成
            embed = discord.Embed(
                title=f"👑 {target_month}月 メッセージ送信数ランキング",
                description="先月最もサーバーを盛り上げてくれたメンバーです！",
                color=0x00BFFF # ディープスカイブルー
            )
            
            # 順位に応じてメダル絵文字を付与しながらフィールドに追加
            medals = ["🥇", "🥈", "🥉", "　", "　"]
            for i, (user_id, count) in enumerate(ranking_data):
                member = ctx.guild.get_member(user_id)
                # メンバーが既に退出している場合の対策
                name = member.display_name if member else "不明なユーザー"
                
                embed.add_field(
                    name=f"{medals[i]} 第{i+1}位: {name}",
                    value=f"{count} メッセージ",
                    inline=False
                )

        await target_channel.send(embed=embed)

        # コマンド実行場所と送信先が異なる場合は通知を出す
        if ctx.channel.id != target_channel.id:
            await ctx.send(f"{target_channel.mention} にランキングを送信しました。")

async def setup(bot):
    await bot.add_cog(Ranking(bot))