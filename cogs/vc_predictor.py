import discord
from discord.ext import commands
import csv
import io
import re
from datetime import datetime

class VcPredictor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="exportlog")
    @commands.has_permissions(administrator=True)
    async def export_vc_log(self, ctx, limit: int = 1000):
        """vc-logチャンネルの履歴を取得してrawデータのCSVを出力するコマンド"""
        log_channel = discord.utils.get(ctx.guild.text_channels, name="vc-log")
        if not log_channel:
            await ctx.send("vc-logチャンネルが見つかりません。")
            return

        await ctx.send(f"過去 {limit} 件のrawデータ抽出を開始します...")

        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(["timestamp", "user_id", "user_name", "action", "channel_name"])

        count = 0
        async for message in log_channel.history(limit=limit, oldest_first=False):
            if not message.embeds:
                continue
            
            embed = message.embeds[0]
            
            footer_text = embed.footer.text if embed.footer else ""
            user_id = ""
            action = ""
            if footer_text:
                match = re.search(r"ID:\s*(\d+)\s*\|\s*ACTION:\s*([A-Z]+)", footer_text)
                if match:
                    user_id = match.group(1)
                    action = match.group(2)
            
            description = embed.description if embed.description else ""
            user_name = ""
            channel_name = ""
            
            name_match = re.search(r"\*\*(.+?)\*\*", description)
            if name_match:
                user_name = name_match.group(1)
            
            channels = re.findall(r"'(.*?)'", description)
            if channels:
                if action == "MOVE" and len(channels) >= 2:
                    channel_name = f"{channels[0]} -> {channels[1]}"
                else:
                    channel_name = channels[0]

            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")

            writer.writerow([timestamp, user_id, user_name, action, channel_name])
            count += 1

        csv_file.seek(0)
        discord_file = discord.File(
            fp=io.BytesIO(csv_file.getvalue().encode('utf-8-sig')), 
            filename="vclog_raw.csv"
        )
        
        await ctx.send(f"rawデータの抽出が完了しました（{count}件）", file=discord_file)

    @commands.command(name="preprocess")
    @commands.has_permissions(administrator=True)
    async def preprocess_vc_log(self, ctx, limit: int = 1000):
        """vc-logチャンネルの履歴からセッションデータを生成してCSVで出力するコマンド"""

        log_channel = discord.utils.get(ctx.guild.text_channels, name="vc-log")
        if not log_channel:
            await ctx.send("vc-logチャンネルが見つかりません。")
            return

        await ctx.send(f"過去 {limit} 件のログからセッションデータの作成を開始します...")

        sessions = [] # [user_id, user_name, join_time, leave_time, duration_seconds]
        active_sessions = {} # user_id: {"user_name": name, "join_time": datetime}

        # セッション化のため、時系列順(oldest_first=True)で処理
        async for message in log_channel.history(limit=limit, oldest_first=True):
            if not message.embeds:
                continue
            
            embed = message.embeds[0]
            footer_text = embed.footer.text if embed.footer else ""
            if not footer_text: continue

            match = re.search(r"ID:\s*(\d+)\s*\|\s*ACTION:\s*([A-Z]+)", footer_text)
            if not match: continue

            user_id = match.group(1)
            action = match.group(2)

            description = embed.description if embed.description else ""
            user_name = ""
            name_match = re.search(r"\*\*(.+?)\*\*", description)
            if name_match:
                user_name = name_match.group(1)

            timestamp = message.created_at
            
            if action == "JOIN":
                # 新しいセッションを開始
                active_sessions[user_id] = {"user_name": user_name, "join_time": timestamp}
            
            elif action == "LEAVE":
                # 進行中のセッションがあれば終了時刻と滞在時間を計算して記録
                if user_id in active_sessions:
                    join_time = active_sessions[user_id]["join_time"]
                    duration = (timestamp - join_time).total_seconds()
                    
                    sessions.append([
                        user_id,
                        user_name,
                        join_time.strftime("%Y-%m-%d %H:%M:%S"),
                        timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        int(duration)
                    ])
                    del active_sessions[user_id]
            
            elif action == "MOVE":
                # VC間の移動は滞在継続とみなす。ログ取得範囲外でJOINしていた場合の補完も行う
                if user_id not in active_sessions:
                    active_sessions[user_id] = {"user_name": user_name, "join_time": timestamp}

        csv_file = io.StringIO()
        writer = csv.writer(csv_file)
        writer.writerow(["user_id", "user_name", "join_time", "leave_time", "duration_seconds"])

        for session in sessions:
            writer.writerow(session)

        csv_file.seek(0)
        discord_file = discord.File(
            fp=io.BytesIO(csv_file.getvalue().encode('utf-8-sig')), 
            filename="vclog_session.csv"
        )
        
        await ctx.send(f"セッションデータの作成が完了しました（{len(sessions)}セッション）", file=discord_file)

async def setup(bot):
    await bot.add_cog(VcPredictor(bot))