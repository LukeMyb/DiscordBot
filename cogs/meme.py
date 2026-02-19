import discord
from discord.ext import commands
from PIL import Image
import io
import os

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.dragon_path = "assets/sukina-souzai-happyo-dragon.png"
        self.robo_path = "assets/maji-res-robo.png"

    @commands.command()
    async def dragon(self, ctx):
        if not os.path.exists(self.dragon_path): #ファイルの有無を確認
            await ctx.send(f"エラー: {self.dragon_path} が見つかりません。")
            return
        
        async with ctx.typing():
            try:
                with Image.open(self.dragon_path) as img: #Pillowで画像を開く
                    buffer = io.BytesIO() #メモリ上のバッファに保存
                    img.save(buffer, format="PNG")
                    buffer.seek(0) #バッファの先頭に戻る

                    file = discord.File(fp=buffer, filename="output.png") #Discordにファイルを送信
                    await ctx.send("", file=file)
            except Exception as e:
                await ctx.send(f"画像処理中にエラーが発生しました: {e}")
    
    @commands.command()
    async def robo(self, ctx):
        if not os.path.exists(self.robo_path): #ファイルの有無を確認
            await ctx.send(f"エラー: {self.robo_path} が見つかりません。")
            return
        
        async with ctx.typing():
            try:
                with Image.open(self.robo_path) as img: #Pillowで画像を開く
                    buffer = io.BytesIO() #メモリ上のバッファに保存
                    img.save(buffer, format="PNG")
                    buffer.seek(0) #バッファの先頭に戻る

                    file = discord.File(fp=buffer, filename="output.png") #Discordにファイルを送信
                    await ctx.send("", file=file)
            except Exception as e:
                await ctx.send(f"画像処理中にエラーが発生しました: {e}")

async def setup(bot):
    await bot.add_cog(Meme(bot))