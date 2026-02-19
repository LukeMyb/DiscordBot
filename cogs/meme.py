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
class DrawProps: #吹き出しのプロパティ
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
        size=Size(w=430-100, h=230-110), 
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
        font_size = dp.base_font_size #文字のサイズ
        line_spacing = 5 #行間

        #枠に収まるフォントサイズと行分割を探すループ
        while font_size > 10:
            font = self.get_font(font_size) #フォントの適用
            lines = [] #改行を含めた文章全体(要素間が改行を表す)
            current_line = "" #現在扱っている文章(改行なし)
            
            #指定の幅(dp.size.w)で自動改行処理
            for char in text:
                test_line = current_line + char
                if font.getlength(test_line) <= dp.size.w: #枠内に収まるなら改行なしでcharを文章に追加
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char #新たなラインを開始
            lines.append(current_line)
            
            #全体の高さを計算
            line_h = font.getbbox("あ")[3] - font.getbbox("あ")[1] #bbox[3] - bbox[1] (上端 - 下端)
            total_h = len(lines) * line_h + (len(lines) - 1) * line_spacing #行数*文字の高さ + 行間の数*行間の高さ
            
            #枠の高さ(dp.size.h)に収まればループ終了
            if total_h <= dp.size.h:
                break
            font_size -= 2 #はみ出すならサイズを下げてやり直し

        #枠の中心
        center_x = dp.pos.x + dp.size.w // 2
        center_y = dp.pos.y + dp.size.h // 2

        #文章全体が上下中央に来るように開始位置を計算
        start_y = center_y - (total_h // 2) + (line_h // 2) #枠の中心座標 - 枠の高さの半分 + 文字の高さの半分
        
        for i, line in enumerate(lines): #ラインごとに出力
            y = start_y + i * (line_h + line_spacing) #行が変わったらその分yを下にずらす
            draw.text((center_x, y), line, font=font, fill=(0, 0, 0), anchor="mm")

    async def process_meme(self, ctx, template_path, dp, text):
        if not os.path.exists(template_path): #ファイルの有無を確認
            await ctx.send(f"エラー: {template_path} が見つかりません。")
            return
        
        async with ctx.typing():
            try:
                with Image.open(template_path).convert("RGBA") as img: #画像を開く
                    self.draw_text(ImageDraw.Draw(img), text, dp) #画像に文字を出力

                    buffer = io.BytesIO() #メモリ上のバッファに保存
                    img.save(buffer, format="PNG")
                    buffer.seek(0) #バッファの先頭に戻る
                    await ctx.send(file=discord.File(fp=buffer, filename="output.png")) #Discordにファイルを送信

                    #ユーザーのコマンド入力を削除
                    try:
                        await ctx.message.delete()
                    except discord.Forbidden: #権限がない場合は無視
                        pass
                    except discord.HTTPException: #その他の接続エラーも無視
                        pass
            except Exception as e:
                await ctx.send(f"画像処理中にエラーが発生しました: {e}")

    @commands.command()
    async def dragon(self, ctx, *, text: str):
        await self.process_meme(ctx, self.dragon_path, MEME_CONFIG["dragon"], text)
    
    @commands.command()
    async def robo(self, ctx, *, text: str):
        await self.process_meme(ctx, self.robo_path, MEME_CONFIG["robo"], text)

async def setup(bot):
    await bot.add_cog(Meme(bot))