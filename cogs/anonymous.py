import discord
from discord.ext import commands

#匿名メッセージを入力するためのModal(ポップアップ)画面
class AnonymousModal(discord.ui.Modal, title="匿名メッセージ作成"):
    message = discord.ui.TextInput(
        label="内容",
        style=discord.TextStyle.paragraph, #入力欄のスタイルを長文用に
        placeholder="内容を入力...", #入力欄が空欄のときに表示されるヒントテキスト
        required=True, #内容が空だと送信できないように
        max_length=1000
    )

    #メッセージを送信
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer() #処理が終わるまで待機
        
        #ユーザーIDから固定の4桁IDを生成(あまり + ハッシュ関数で少し複雑化)
        import zlib
        user_hash = zlib.adler32(str(interaction.user.id).encode()) % 10000
        anon_id = f"{user_hash:04d}" #0埋めして4桁に

        #過去のボタン削除
        async for msg in interaction.channel.history(limit=10):
            if msg.author == interaction.client.user and msg.components: #ボタンがついたメッセージを特定
                old_embed = msg.embeds[0] if msg.embeds else None #内容を一時的に保存
                await msg.delete()
                if old_embed:
                    await interaction.channel.send(embed=old_embed) #ボタンを消して再送信
                break

        #新しい匿名メッセージの構築
        new_embed = discord.Embed(
            description=self.message.value,
            color=discord.Color.default()
        )
        #著者欄に「匿名:1234」と「デフォルトアイコン」をセット
        new_embed.set_author(
            name=f"匿名:{anon_id}",
            icon_url=interaction.user.default_avatar.url #デフォルトの卵アイコン
        )
        
        await interaction.channel.send(embed=new_embed, view=AnonymousView())

#メッセージに付属させるボタン(View)
class AnonymousView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) #タイムアウトを無効化

    @discord.ui.button(label="匿名で発言する", style=discord.ButtonStyle.primary, custom_id="anonymous_button")
    async def anonymous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AnonymousModal()) #Modalを開く

class Anonymous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    #ボットが再起動したときボタンを再び有効化
    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(AnonymousView())

    @commands.command(name="setup_anonymous")
    @commands.has_permissions(administrator=True)
    async def setup_anonymous(self, ctx: commands.Context):
        target_channel = discord.utils.get(ctx.guild.text_channels, name="匿名会話") #「匿名会話」という名前のチャンネルを特定

        if not target_channel:
            await ctx.reply("エラー：「匿名会話」という名前のチャンネルが見つかりません。")
            return

        embed = discord.Embed(
            title="匿名チャット開始",
            description="このメッセージのボタン、または以降の匿名発言に付いているボタンから発言できます。",
            color=discord.Color.dark_gray()
        )
        
        await target_channel.send(embed=embed, view=AnonymousView())
        await ctx.reply(f"{target_channel.mention} に初期ボタンを設置しました。")


async def setup(bot):
    await bot.add_cog(Anonymous(bot))