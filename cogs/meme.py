import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
from dataclasses import dataclass
from typing import Literal

@dataclass
class Pos: #描画の開始位置(左上の座標)
    x: int
    y: int

@dataclass
class Size: #描画を許可する範囲(幅と高さ)
    w: int
    h: int

@dataclass
class DrawProps:
    pos: Pos
    size: Size
    base_font_size: int

MEME_CONFIG = {
    "dragon": DrawProps(
        pos=Pos(x=180, y=140), 
        size=Size(w=520-180, h=360-140), 
        base_font_size=80, 
    ),
    "robo": DrawProps(
        pos=Pos(x=100, y=110), 
        size=Size(w=430, h=230), 
        base_font_size=25, 
    ),
}

class Meme(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        #テンプレート画像とフォント
        self.dragon_path = "assets/sukina-souzai-happyo-dragon.png"
        self.robo_path = "assets/maji-res-robo.png"
        self.font_path = "assets/Futehodo-MaruGothic.otf"

    def get_font(self, size):
        #フォントを読み込む(失敗したらデフォルトを適用)
        try:
            return ImageFont.truetype(self.font_path, size)
        except OSError:
            return ImageFont.load_default()
        
    def draw_text(self, draw, text, dp: DrawProps):
        #枠の中心
        center_x = dp.pos.x + dp.size.w // 2
        center_y = dp.pos.y + dp.size.h // 2

        text_size = dp.base_font_size #文字のサイズ

        while text_size > 10: #枠内に収まるまでフォントサイズを2pxずつ下げる
            font = self.get_font(text_size)
            if font.getlength(text) <= dp.size.w: #実際に描画したときの幅 <= 枠の幅
                break
            text_size -= 2

        #anchor="mm"は中央揃え
        draw.text((center_x, center_y), text, font=font, fill=(0, 0, 0), anchor="mm")

    @commands.command()
    async def dragon(self, ctx, *, text: str):
        dp = MEME_CONFIG["dragon"] #吹き出しのデータ

        if not os.path.exists(self.dragon_path): #ファイルの有無を確認
            await ctx.send(f"エラー: {self.dragon_path} が見つかりません。")
            return
        
        async with ctx.typing():
            try:
                with Image.open(self.dragon_path).convert("RGBA") as img: #画像を開く
                    draw = ImageDraw.Draw(img)
                    self.draw_text(draw, text, dp) #画像に文字を出力

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
                with Image.open(self.robo_path).convert("RGBA") as img: #Pillowで画像を開く
                    buffer = io.BytesIO() #メモリ上のバッファに保存
                    img.save(buffer, format="PNG")
                    buffer.seek(0) #バッファの先頭に戻る

                    file = discord.File(fp=buffer, filename="output.png") #Discordにファイルを送信
                    await ctx.send("", file=file)
            except Exception as e:
                await ctx.send(f"画像処理中にエラーが発生しました: {e}")

async def setup(bot):
    await bot.add_cog(Meme(bot))