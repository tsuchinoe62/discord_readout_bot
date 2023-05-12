import asyncio
import datetime
import os
import re
import discord

from dotenv import load_dotenv
from discord.commands.context import ApplicationContext
from discord.commands import option
from discord.ext import pages

import voice_text
import shindan_maker
import database


intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = discord.Bot(intents=intents)

# 環境変数の読み込み
load_dotenv()
TOKEN: str = os.environ.get("BOT")
VOICETEXT_API_KEY: str = os.environ.get("VOICETEXT")


voice_clients: dict[int, discord.voice_client.VoiceClient] = {}
text_channels: dict[int, discord.TextChannel] = {}


@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}")


@bot.slash_command(description="使い方を表示するで。")
async def help(ctx: ApplicationContext):
    embed_main: discord.Embed = discord.Embed(title="喋三郎", description="メッセージを読み上げるBOTやで。")
    embed_main.add_field(name="/summon",  value="わいをボイスチャンネルに呼ぶコマンドや。", inline=False)
    embed_main.add_field(name="/bye",     value="わいをボイスチャンネルから追い出す時に使うんや。", inline=False)
    embed_main.add_field(name="/stop",    value="わいが喋ってるのを黙らせるで。", inline=False)
    embed_main.add_field(name="/inspect", value="summonコマンドが反応せんくなった時に使ってみてや。", inline=False)
    embed_main.add_field(name="/shindan", value="診断メーカーから適当に診断を選ぶで。", inline=False)

    embed_voice: discord.Embed = discord.Embed(title="音声設定", description="メッセージを読み上げる音声の設定やで。")
    embed_voice.add_field(name="/speaker",           value="話者を変えるで。show(男性)、haruka(女性)、hikari(女性)、takeru(男性)、santa(サンタ)、bear(凶暴なクマ)から選択できるで。")
    embed_voice.add_field(name="/pitch",             value="声の高さを変えるで。50～200の整数を指定できて、値が小さいほど低い音になるで。デフォルトは100や。")
    embed_voice.add_field(name="/speed",             value="話す速度を変えるで。50～400の整数を指定できて、値が小さいほど遅い話し方になるで。デフォルトは100や。")
    embed_voice.add_field(name="/emotion",           value="感情を変えるで。happiness(喜)、anger(怒)、sadness(悲)、default(無)から選択できるで。感情は話者がharuka, hikari, takeru, santa, bearのときだけ有効やで。")
    embed_voice.add_field(name="/emotion_level",     value="感情の強さを変えるで。1～4の整数を指定できて、数値が大きいほど感情が強くなるで。デフォルトは2や。")
    embed_voice.add_field(name="/get_voice_setting", value="今の音声設定を表示するで。")

    embed_guild: discord.Embed = discord.Embed(title="読み上げ設定", description="サーバー毎の設定やで。")
    embed_guild.add_field(name="/read_name", value="名前を読み上げるか設定するで。デフォルトはTrueや。")
    embed_guild.add_field(name="/read_bot",  value="わいを含むBOTの発言を読み上げるか設定するで。デフォルトはTrueや。")

    embed_dictionary: discord.Embed = discord.Embed(title="サーバー", description="サーバー毎の設定やで。")
    embed_dictionary.add_field(name="/wbook add",    value="単語を登録するで。")
    embed_dictionary.add_field(name="/wbook list",   value="登録された単語の一覧を表示するで。")
    embed_dictionary.add_field(name="/wbook delete", value="登録された単語を削除するで。")

    paginator = pages.Paginator(pages=[embed_main, embed_voice, embed_guild, embed_dictionary])

    await paginator.respond(ctx.interaction)


@bot.slash_command(description="わいをボイスチャンネルに召喚するコマンドやで。間違っても/suumoとか/sermonとか打ったらあかんで。")
async def summon(ctx: ApplicationContext):
    global voice_clients
    global text_channels

    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    guild_id: int = ctx.guild.id
    print(f"{ctx.guild.name}/{ctx.author.name}: /summon")

    author_voice_state: discord.VoiceState | None = ctx.author.voice

    # 召喚した人がボイスチャンネルにいるか判定
    if author_voice_state is not None:
        # サーバーで初めて召喚された場合、サーバーの情報をDBに登録
        database.insert_guild(guild_id, ctx.guild.name)

        # 召喚された時、voice_clientsに情報が残っていたら削除
        if guild_id in voice_clients:
            await voice_clients[guild_id].disconnect()
            del voice_clients[guild_id]
            del text_channels[guild_id]

        try:
            voice_clients[guild_id] = await author_voice_state.channel.connect(timeout=10.0)
        except asyncio.TimeoutError:
            await ctx.send("召喚できひんかった。わいのせいとちゃう。DiscordのAPIサーバーが応答せんかったんや。")
            return

        text_channels[guild_id]  = ctx.channel

        await ctx.respond("毎度おおきに。わいは喋三郎や。/helpコマンドで使い方を表示するで。")
    else:
        await ctx.respond("あんたボイスチャンネルおらへんやんけ！")


@bot.slash_command(description="わいをボイスチャンネルから追い出すコマンドやで。")
async def bye(ctx: ApplicationContext):
    global voice_clients
    global text_channels

    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    guild_id: int = ctx.guild.id
    print(f"{ctx.guild.name}/{ctx.author.name}: /bye")

    if guild_id in text_channels and ctx.channel_id == text_channels[guild_id].id:
        while voice_clients[guild_id].is_playing():
            await asyncio.sleep(1)

        await voice_clients[guild_id].disconnect()
        await ctx.respond("じゃあの")

        del voice_clients[guild_id]
        del text_channels[guild_id]
    else:
        await ctx.respond("召喚されてへんで～")


@bot.slash_command(description="わいが喋ってるのを黙らせるで。")
async def stop(ctx: ApplicationContext):
    global voice_clients

    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    guild_id: int = ctx.guild.id
    print(f"{ctx.guild.name}/{ctx.author.name}: /stop")

    if guild_id in voice_clients:
        voice_client: discord.voice_client.VoiceClient = voice_clients[guild_id]
        if voice_client.is_playing():
            voice_client.stop()
        else:
            await ctx.respond("なんも言うてへんで")
    else:
        await ctx.respond("召喚されてへんで～")


@bot.slash_command(description="summonコマンドに応答せん時に使ってみてや。このコマンドも反応せんかったらBOTが死んでるで。")
async def inspect(ctx: ApplicationContext):
    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    print(f"{ctx.guild.name}/{ctx.author.name}: /inspect")

    await ctx.response.defer(invisible=False)

    await ctx.send("チャンネルにBOTが残ってないか確認するで。")
    guild_id: int = ctx.guild.id

    if guild_id in text_channels:
        await ctx.send("召喚コマンドが実行されたテキストチャンネルにBOTの情報がまだ残っとった。")
        del text_channels[guild_id]
        await ctx.send("召喚コマンドが実行されたテキストチャンネルからBOTの情報を削除したで。")
    else:
        await ctx.send("召喚コマンドが実行されたテキストチャンネルにBOTの情報は残っとらんかった。")

    if guild_id in voice_clients:
        await ctx.send("召喚されたボイスチャンネルにBOTの情報がまだ残っとった")
        await voice_clients[guild_id].disconnect()
        await ctx.send("ボイスチャンネルからBOTを切断したで。")
        del voice_clients[guild_id]
        await ctx.send("召喚されたボイスチャンネルからBOTの情報を削除したで。")
    else:
        await ctx.send("召喚されたボイスチャンネルにBOTの情報は残っとらんかった。")

    await ctx.send("VoiceText APIへの疎通確認をしてみるで。")
    try:
        voice_cache = await voice_text.call_api(
            api_key=VOICETEXT_API_KEY,
            text="テスト",
            format="mp3"
        )
        os.remove(voice_cache)
        await ctx.send("VoiceTextのAPIサーバーは応答したで。")
    except Exception as exception:
        await ctx.send(f"VoiceTextのAPIサーバーが応答せんかった。{exception}")

    await ctx.respond("終了や。summonコマンドで再接続してみてや。")


@bot.slash_command(description="コマンドの後に「True」か「False」をつけることで、名前を読み上げるか切り替えられるで。")
async def read_name(ctx: ApplicationContext, value: bool):
    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    print(f"{ctx.guild.name}/{ctx.author.name}: /read_name")

    database.update_guild(ctx.guild_id, {"read_name": value})

    if value is True:
        await ctx.respond("名前を読み上げるようにしたで。")
    else:
        await ctx.respond("名前を読み上げへんようにしたで。")


@bot.slash_command(description="コマンドの後に「True」か「False」をつけることで、BOTの発言を読み上げるか切り替えられるで。")
async def read_bot(ctx: ApplicationContext, value: bool):
    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    print(f"{ctx.guild.name}/{ctx.author.name}: /read_bot")

    database.update_guild(ctx.guild_id, {"read_bot": value})

    if value is True:
        await ctx.respond("BOTの発言を読み上げるようにしたで。")
    else:
        await ctx.respond("BOTの発言を読み上げへんようにしたで。")


async def get_speakers(ctx: discord.AutocompleteContext):
    return voice_text.SPEAKER_LIST


@bot.slash_command(description="コマンドの後にshow, haruka, hikari, takeru, santa, bearのどれかをつけると、声を変えられるで。")
@option("value",
        description="show(男性)、haruka(女性)、hikari(女性)、takeru(男性)、santa(サンタ)、bear(凶暴なクマ)",
        autocomplete=discord.utils.basic_autocomplete(get_speakers))
async def speaker(ctx: ApplicationContext, value: str):
    if value not in voice_text.SPEAKER_LIST:
        await ctx.respond("値が正しくないで。show, haruka, hikari, takeru, santa, bearのどれかを指定してや。")
        return

    database.update_user(ctx.author.id, {"speaker": value})

    await ctx.respond(f"話者を{value}に設定したで。")


@bot.slash_command(description="コマンドの後に50～200の整数をつけると、声の高さを変えるで。デフォルトは100や。")
@option("value", description="50～200の整数")
async def pitch(ctx: ApplicationContext, value: int):
    if value < 50 or value > 200:
        await ctx.respond("値が正しくないで。50～200の整数で入力してや。")
        return

    database.update_user(ctx.author.id, {"pitch": value})

    await ctx.respond(f"声の高さを{value}に設定したで。")


@bot.slash_command(description="コマンドの後に50～400の整数をつけると、読み上げの速さを変えられるで。デフォルトは100や。")
@option("value", description="50～400の整数")
async def speed(ctx: ApplicationContext, value: int):
    if value < 50 or value > 400:
        await ctx.respond("値が正しくないで。50～400の整数で入力してや。")
        return

    database.update_user(ctx.author.id, {"speed": value})

    await ctx.respond(f"読み上げの速さを{value}に設定したで。")


async def get_emotions(ctx: discord.AutocompleteContext):
    return voice_text.EMOTION_LIST + ["default"]


@bot.slash_command(description="コマンドの後に「happiness」、「anger」、「sadness」、「default」のどれかをつけると、感情を変えられるで。")
@option("value",
        description="happiness(喜)、anger(怒)、sadness(悲)、default(無)",
        autocomplete=discord.utils.basic_autocomplete(get_emotions))
async def emotion(ctx: ApplicationContext, value: str):
    emotion_list = voice_text.EMOTION_LIST + ["default"]
    if value not in emotion_list:
        await ctx.respond("値が正しくないで。happiness, anger, sadness, defaultのどれかを指定してや。")
        return

    if value == "default":
        database.update_user(ctx.author.id, {"emotion": ""})
        await ctx.respond("感情をデフォルトに設定したで。")
    else:
        database.update_user(ctx.author.id, {"emotion": value})
        await ctx.respond(f"感情を{value}に設定したで。")


@bot.slash_command(description="コマンドの後に1から4の整数をつけると、感情の強さを変えられるで。デフォルトは2や。")
@option("value", description="1～4の整数")
async def emotion_level(ctx: ApplicationContext, value: int):
    if value < 1 or value > 4:
        await ctx.respond("値が正しくないで。1～4の整数で入力してや。")
        return

    database.update_user(ctx.author.id, {"emotion_level": value})

    await ctx.respond(f"感情の強さを{value}に設定したで。")


@bot.slash_command(description="現在の声の設定を確認できるで。")
async def get_voice_setting(ctx: ApplicationContext):
    user = database.search_user(ctx.author.id)

    if user is None:
        return

    embed = discord.Embed(title="音声設定")
    embed.add_field(name="話者",     value=user["speaker"], inline=False)
    embed.add_field(name="高さ",     value=user["pitch"], inline=False)
    embed.add_field(name="速さ",     value=user["speed"], inline=False)
    embed.add_field(name="感情",     value=user["emotion"], inline=False)
    embed.add_field(name="感情強度", value=user["emotion_level"], inline=False)

    await ctx.respond(embed=embed)

wbook = discord.SlashCommandGroup("wbook", "辞書登録関連のコマンドやで。")


@wbook.command(description="読み方を登録するで。")
@option("word", description="単語")
@option("read", description="よみがな")
async def add(ctx: ApplicationContext, word: str, read: str):
    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    dictionary = database.insert_dictionary(ctx.guild.id, word, read)
    print(dictionary)
    await ctx.respond(f"{word}を登録したで。")


@wbook.command(description="読み方を削除するで。")
@option("id", description="削除する単語の番号")
async def delete(ctx: ApplicationContext, id: int):
    if ctx.guild is None:
        await ctx.respond("DMでそのコマンドは使えへんで。")
        return

    dictionary = database.delete_dictionary(ctx.guild.id, id)
    if dictionary is not None:
        await ctx.respond(f"{id}番を削除したで。")
    else:
        await ctx.respond(f"{id}番はないで。")


@wbook.command(description="登録された読み方の一覧を表示するで。")
async def list(ctx: ApplicationContext):
    dictionaries = database.search_dictionary(ctx.guild.id)

    embed = discord.Embed(title="辞書一覧")
    embed.add_field(name="番号", value="単語:よみがな", inline=False)
    for dictionary in dictionaries:
        embed.add_field(name=dictionary.doc_id, value=f"{dictionary['word']}:{dictionary['read']}")

    await ctx.respond(embed=embed)

bot.add_application_command(wbook)


# ネタコマンド
@bot.slash_command(description="コマンドを実行する前にスペルを確認してみ。")
async def suumo(ctx: ApplicationContext):
    await ctx.respond("\
        あ❗️  スーモ❗️ 🌚 ダン💥 ダン💥 ダン💥 シャーン🎶\
        スモ🌝 スモ🌚 スモ🌝 スモ🌚 スモ🌝 スモ🌚 ス〜〜〜モ⤴\
        スモ🌚 スモ🌝 スモ🌚 スモ🌝 スモ🌚 スモ🌝 ス～～～モ⤵ 🌞\
    ")


@bot.slash_command(description="コマンドを実行する前にスペルを確認してみ。")
async def sermon(ctx: ApplicationContext):
    await ctx.respond("コラー！！summonとか言う簡単なコマンドを間違えよってからにアンタはホンマ！！")


@bot.slash_command(description="診断メーカーのPICKUP診断から適当に診断を選ぶで")
async def shindan(ctx: ApplicationContext):
    shindan_link = shindan_maker.get_shindan_link()
    if shindan_link is not None:
        await ctx.respond(shindan_link)
    else:
        await ctx.respond("取得できひんかった")


@bot.event
async def on_message(message: discord.message.Message):
    global voice_clients
    global text_channels

    # BOTへのDMの場合
    if message.guild is None:
        if message.author.bot is False:
            print(f"DM/{message.author.name}: {message.content}")
            await message.channel.send("お問い合わせは@tsuchinoe#1645までお願いします。")
        return

    print(f"{message.guild.name}/{message.author.nick or message.author.name}: {message.content}")

    guild_id = message.guild.id

    # 召喚されていなかった場合は何もしない
    if guild_id not in text_channels:
        return

    # summonコマンドが実行されたテキストチャンネルと異なるテキストチャンネルのメッセージは無視する
    if message.channel.id != text_channels[guild_id].id:
        return

    # BOTの発言を読み上げない設定の場合、BOTの発言は無視する
    guild = database.search_guild(guild_id)
    if guild["read_bot"] is False and message.author.bot is True:
        return

    # 名前を読み上げる設定が有効の場合、文頭に名前を挿入
    message_content: str = message.content
    if guild["read_name"] is True:
        message_content = f"{message.author.nick or message.author.name}、{message_content}"

    # summonコマンドが実行されたテキストチャンネルでメッセージを受信したら読み上げる

    # userの情報がDBに無ければ登録
    user: dict = database.insert_user(message.author.id, message.author.name)

    # URLを"URL"に置換
    message_content = re.sub(r"https?://[\w/:%#\$&\?\(\)~\.=\+\-]+", "URL", message_content)
    # カスタム絵文字の変換 (例: あいうえお<:hoge:123456789>かきくけこ -> あいうえお<:hoge:>かきくけこ)
    message_content = re.sub(r":\d*", ":>", message_content)

    # ユーザーへのメンションの変換
    mentions: list[str] = re.findall(r"<@(\d+)>", message_content)
    for mention in mentions:
        member = message.guild.get_member(int(mention))
        if member:
            message_content = message_content.replace(f"<@{mention}>", member.display_name)

    # ロールへのメンションの変換
    mentions: list[str] = re.findall(r"<@&(\d+)>", message_content)
    for mention in mentions:
        role = message.guild.get_role(int(mention))
        if role:
            message_content = message_content.replace(f"<@&{mention}>", role.name)

    # チャンネル、スレッドへのメンションの変換
    mentions: list[str] = re.findall(r"<#(\d+)>", message_content)
    for mention in mentions:
        channel = message.guild.get_channel_or_thread(int(mention))
        if channel:
            message_content = message_content.replace(f"<#{mention}>", channel.name)

    # 辞書登録された単語を変換
    dictionaries = database.search_dictionary(guild_id)
    for dictionary in dictionaries:
        message_content = message_content.replace(dictionary["word"], dictionary["read"])

    if message_content == "":
        return

    try:
        print(message_content)
        voice_cache = await voice_text.call_api(
            api_key=VOICETEXT_API_KEY,
            text=message_content,
            speaker=user["speaker"],
            pitch=user["pitch"],
            speed=user["speed"],
            emotion=user["emotion"],
            emotion_level=user["emotion_level"],
            format="mp3"
        )
    except Exception as exception:
        print(exception)
        await message.channel.send("VoiceTextのAPIサーバーが応答せんかった。")
        return

    if guild_id in voice_clients:
        while voice_clients[guild_id].is_playing():
            await asyncio.sleep(1)

        voice_clients[guild_id].play(discord.FFmpegPCMAudio(voice_cache))
        print(f"Play {voice_cache}")

        while voice_clients[guild_id].is_playing():
            await asyncio.sleep(1)
    else:
        print("ボイスチャンネルにBOTがいない")
    os.remove(voice_cache)


@bot.event
async def on_voice_state_update(
    member: discord.member.Member,
    before: discord.member.VoiceState,
    after: discord.member.VoiceState
):
    global voice_clients
    global text_channels

    print(f"member: {member}\nbefore: {before}\nafter: {after}")

    # ミュートの操作等の場合は何もしない
    if before.channel == after.channel:
        return

    # 誰かがボイスチャンネルに入室した場合
    if after.channel is not None:
        guild_id = after.channel.guild.id

        # BOTが召喚されていない場合は何もしない
        if guild_id not in text_channels:
            return

        # BOTがいるボイスチャンネル以外に入室した場合は何もしない
        if voice_clients[guild_id].channel.id != after.channel.id:
            return

        current_hour = datetime.datetime.now().hour
        if current_hour <= 4 or current_hour >= 18:
            greet = "こんばんは"
        elif 5 <= current_hour <= 10:
            greet = "おはよう"
        elif 11 <= current_hour <= 17:
            greet = "こんにちは"

        await text_channels[guild_id].send(f"{member.nick or member.name}さん、{greet}やで")
    # 退室の場合
    elif after.channel is None:
        guild_id = before.channel.guild.id

        # BOTが召喚されていない場合は何もしない
        if guild_id not in text_channels:
            return

        # BOTがいるボイスチャンネル以外に入室した場合は何もしない
        if voice_clients[guild_id].channel.id != before.channel.id:
            return

        await text_channels[guild_id].send(f"{member.nick or member.name}さん、じゃあの")

        # BOT以外の全員が退出した場合
        if guild_id in voice_clients:
            voice_channel_members = voice_clients[guild_id].channel.members
            if len(voice_channel_members) == 1 and voice_channel_members[0].bot is True:
                while voice_clients[guild_id].is_playing():
                    await asyncio.sleep(1)

                await voice_clients[guild_id].disconnect()
                await text_channels[guild_id].send("誰も居らんくなった。じゃあの")

                del voice_clients[guild_id]
                del text_channels[guild_id]


bot.run(TOKEN)
