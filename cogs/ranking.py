import discord
from discord.ext import commands
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

    # 手動確認用コマンド
    @commands.command(name="ranking")
    async def show_ranking(self, ctx):
        # 処理に時間がかかる可能性があるため、入力中(typing)のアクションを表示
        async with ctx.typing():
            ranking_data, target_month = await self.get_monthly_ranking(ctx.guild)
            
            if not ranking_data:
                await ctx.send(f"{target_month}月のメッセージデータが見つかりませんでした。")
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

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Ranking(bot))