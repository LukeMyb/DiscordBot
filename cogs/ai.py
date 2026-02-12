import discord
from discord.ext import commands
import os
import re #正規表現を扱う (特定のルール(パターン)に基づいた文字の塊を見つけ出し, 自由自在に加工する)
import csv
from janome.tokenizer import Tokenizer #品詞分解
from datetime import datetime
import json
import random

class Ai(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        self.my_dict = self.load_dict()

    def clean_text(self, text: str): #学習時にノイズとなる文字列を削除
        text = re.sub(r'https?://[\w/:%#\$&\?\(\)~\.=\+\-@]+', '', text) #URLを削除
        text = re.sub(r'<[@#&]!?\d+>', '', text) #メンション・チャンネルリンクを削除
        text = re.sub(r'@everyone|@here', '', text) #@everyoneと@hereを削除
        text = re.sub(r'@\S+', '', text) #@から始まる単語(SNSハンドルやURLの残骸)を削除
        text = re.sub(r'<a?:\w+:\d+>', '', text) #カスタム絵文字を削除
        text = re.sub(r'\n+', '\n', text) #連続する改行を1つの改行に変換
        return text.strip() #前後の余計な空白を消して, 中身があれば返す
    
    def write2csv(self, data: list):
        with open("data/conv_data.csv", "a", encoding="utf-8-sig", newline="") as file: #newline=""は改行コードの自動変換をしないように, -sigはexcelで文字化けしなくなるらしい
            writer = csv.writer(file)
            writer.writerows(data)

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def get_conv(self, ctx): #学習データを抽出
        if not os.path.exists("data/conv_data.csv"): #csvファイルが無かったらヘッダーをつけて作成
            self.write2csv([["timestamp", "user_id", "message_content"]])

        status_msg = await ctx.send("会話データの取得を開始します。時間がかかる場合があります...")
        count: int = 0 #取得したメッセージ数
        data: list = [] #csvに書き込む前に一時的にリストに保存
        for channel in ctx.guild.text_channels: #全チャンネルを探索
            if channel.id in [1280150783161143297, 1280292202949644369, 1317465310403624990, 1469285650036686858]: continue #通話募集用のチャンネルなどは学習データに含めない

            try:
                async for message in channel.history(limit=None, oldest_first=True): #チャンネル内の全メッセージを探索
                    if message.author.bot: continue #botならスルー
                    cleaned: str = self.clean_text(message.content)
                    if cleaned and len(cleaned) >= 2: #中身が空っぽじゃない and 極端に短い単語でなければlistに追加
                        data.append([str(message.created_at), str(message.author.id), cleaned]) #送信時刻, ユーザーid, クレンジングしたメッセージを格納

                    if len(data) == 1000: #リストのメッセージ数が1000を超えたら一旦ファイルに保存
                        self.write2csv(data)
                        count += 1000
                        data = []

                        await status_msg.edit(content=f"取得したメッセージ数: {count}")
                    
                if len(data) != 0:
                    self.write2csv(data)
                    count += len(data)
                    data = []

                    await status_msg.edit(content=f"取得したメッセージ数: {count}")
            except discord.Forbidden:
                pass
            except Exception as e:
                print(e)

        await status_msg.edit(content=f"探索が終了しました\n取得したメッセージ数: {count}")

    @commands.command()
    @commands.has_permissions(administrator=True) #実行者の権限確認
    async def create_dict(self, ctx): #辞書を作成
        status_msg = await ctx.send("辞書の作成を開始します。時間がかかる場合があります...")

        sentences: list = [] #文章をある程度正確に区切ったメッセージ群

        with open("data/conv_data.csv", encoding="utf-8-sig") as file:
            t = Tokenizer()
            reader = csv.reader(file)

            prev_time: datetime
            prev_user: str = ""
            prev_sequence: list = [] #1つ前のメッセージの品詞分解されたリスト

            next(reader) #ヘッダーを除外
            is_first: bool = True #ファイルを読み込んで最初の行か
            for row in reader: #csvの形は timestamp, user id, message content
                tokens = t.tokenize(row[2]) #品詞分解(この時点では品詞などの情報も含まれるオブジェクト)
                
                #品詞などの情報を除外
                token_surface: list = []
                for token in tokens:
                    token_surface.append(token.surface)

                #文章の区切りを追加
                current_user: str = row[1]
                current_time: datetime = datetime.fromisoformat(row[0]) #現在のメッセージの送信時刻
                current_sequence: list = token_surface
                if is_first:
                    current_sequence.insert(0, "[BOS]") #BOS/EOSは文章の開始/終了 (Beginning Of Sentence, End Of Sentence)

                    #1つ前のメッセージの情報を更新して次のループへ
                    prev_sequence = current_sequence
                    is_first = False
                else:
                    #前回のメッセージからの経過時間
                    time_passed: bool
                    if prev_time.hour <= 6:
                        time_passed = (current_time - prev_time).total_seconds() > 3600 * 3 #0~6時は3時間以内のメッセージが返信判定
                    else:
                        time_passed = (current_time - prev_time).total_seconds() > 3600 + 1800 #7時以降は1.5時間以内のメッセージが返信判定

                    if prev_user == current_user and not time_passed: #ユーザーが同じ && 時間が空いてない場合: 1つの文章として結合する
                        prev_sequence.extend(current_sequence)
                    elif prev_user != current_user and not time_passed: #ユーザーが違う && 時間が空いてない場合: 返答として認識
                        prev_sequence.append("[SEP]")
                        prev_sequence += current_sequence
                    elif time_passed: #時間が空いている場合: 新しい文章として認識
                        prev_sequence.append("[EOS]")
                        sentences.append(prev_sequence)
                        current_sequence.insert(0, "[BOS]")

                        prev_sequence = current_sequence #1つ前のメッセージの情報を更新して次のループへ

                #1つ前のメッセージの情報を更新して次のループへ
                prev_time = current_time
                prev_user = current_user
            
            #一番最後のメッセージを追加
            prev_sequence.append("[EOS]")
            sentences.append(prev_sequence)

        await status_msg.edit(content=f"文章を辞書化中...")

        my_dict: dict = {}
        for sentence in sentences:
            for i in range(len(sentence) - 2):
                my_dict.setdefault((sentence[i], sentence[i+1]), []).append(sentence[i+2]) #3-gram(手前2つの単語から次の単語を確率で選ぶ)

        #jsonに保存
        save_dict = {"ㅣ".join(key): value for key, value in my_dict.items()} #json用にタプル型のキーをstrに変換
        with open("data/dict.json", "w", encoding="utf-8") as file:
            json.dump(save_dict, file, ensure_ascii=False, indent=4)

        self.my_dict = self.load_dict() #メモリに反映

        await status_msg.edit(content=f"辞書の作成が完了しました")



    def load_dict(self): #dict.jsonを読み込み
        #dict.jsonの存在を確認
        if not os.path.exists("data/dict.json"):
            print("辞書が見つかりません")
            return {}
        
        #ファイル読み込み
        with open("data/dict.json", mode="r", encoding="utf-8") as file:
            my_dict = json.load(file)
            restored_dict = {tuple(key.split("ㅣ")): value for key, value in my_dict.items()} #キーをstrからタプルに変換
            return restored_dict
        
    @commands.Cog.listener()
    async def on_message(self, message): #メッセージの生成(応答モード)
        if message.author.bot: return
        if message.channel.id != 1469285650036686858: return #AIチャンネルのみで反応するように

        #応答モード
        #ユーザーのメッセージをjanomeで解析し, 品詞分解する
        #名詞をキーワードとしてリストに保持
        #文末の[SEP]を起点に文章を100個くらい生成する(文章を100個生成するときは(ユーザーの文末の2もしくは1単語ㅣ[SEP])で探索してから生成)
        #それぞれの文章に対してスコアリング(キーワードが入っているか)
        #キーワードが含まれてる文章を最優先で出力, どれにも含まれていなければ最も自然なものあるいはランダム

    @commands.command()
    async def generate(self, ctx): #メッセージの生成(独り言モード)
        if ctx.author.bot: return
        if ctx.channel.id != 1469285650036686858: return #AIチャンネルのみで反応するように

        #[BOS]で始まるキーを全部取得
        first: list = []
        for key in self.my_dict.keys():
            if key[0] == "[BOS]":
                first.append(key)

        anss: list = [] #送信するメッセージの候補
        except_ans: int = 0
        generate_msg: int = 1000
        for i in range(generate_msg):
            ans: list = [] #anssの要素の一つ

            #メッセージを1つ生成
            current_key: tuple = random.choice(first) #[BOS]で始まるキーから最初のキーをランダムで選択
            current_value: str = random.choice(self.my_dict[current_key])
            count: int = 0
            while True:
                #生成するメッセージに使用する単語を確定
                if len(ans) == 0:
                    ans.append(current_key[0])
                    ans.append(current_key[1])
                ans.append(current_value)

                if current_value == "[EOS]" or current_value == "[SEP]": break #メッセージの生成を終了
                if count >= 50: break #無限ループに入った場合を考慮して50回で強制終了
                count += 1

                #次の単語へ
                current_key = (current_key[1], current_value)
                current_value = random.choice(self.my_dict[current_key])
            if 5+2 <= len(ans) and len(ans) <= 15+2: #文章が崩壊しないように単語数を制限 (+2は[BOS], [EOS], [SEP]を除外して単語数を考慮するため)
                if "[BOS]" in ans:
                    ans.remove("[BOS]")
                if "[EOS]" in ans:
                    ans.remove("[EOS]")
                if "[SEP]" in ans:
                    ans.remove("[SEP]")

                anss.append(ans) #生成したメッセージをリストに追加
            else:
                except_ans += 1

        print(f"除外されたメッセージ数: {except_ans} / {generate_msg}")
        for ans in anss:
            print("".join(ans))

        await ctx.send(self.scoring(anss)) #スコアリングして最も点数が高い文章をメッセージとして送信

    def scoring(self, anss):
        scores: list = [] #メッセージ群(anss)のインデックスごとに対応させたスコア群

        t = Tokenizer()
        for ans in anss:
            tokens = list(t.tokenize("".join(ans))) #一度一つの文章に結合して再度品詞分解(品詞を特定するため)

            #単語の品詞からスコアリング
            score: int = 0
            for token in tokens:
                #posはpart of speech(品詞)の略
                pos: list = token.part_of_speech.split(',') #token.part_of_speechはlistの形をしたstrだからlistに変換

                if pos[0] == "名詞" and pos[1] != "数": #名詞が1個あれば+10点
                    score += 7
                elif pos[0] == "動詞":
                    score += 5
                elif pos[0] == "形容詞":
                    score += 5
                elif pos[0] == "記号":
                    score -= 5
            
            if tokens[-1].part_of_speech.startswith("助詞"): #文章が助詞で終わるならスコアは0
                score = 0
            
            average: int = score / len(tokens)
            scores.append(average)

        print(f"max_score = {max(scores)}")
        result = anss[scores.index(max(scores))] #(スコアが最大の文章群)の中からインデックスが最小の文章をresultとする
        return "".join(result) #strに変換して返す
        

async def setup(bot):
    await bot.add_cog(Ai(bot))