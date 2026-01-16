import discord
from discord.ext import commands

import json
import sys
import subprocess


# get Discord bot token
secrets_data = {}
with open("secrets.json", "r") as secrets_file: secrets_data = json.load(secrets_file)
if "discord_bot_token" not in secrets_data:
    print("Key \"discord_bot_token\" not found in secrets.json")
    sys.exit(1)

# create bot with correct intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

@bot.event
async def on_ready(): print(f"Logged in as {bot.user}")


status = {
        "read_msgs": False,
        "join_msg": False,
        "member_id": None,
        "text_channel_id": None,
        "voice_channel_id": None
}


@bot.event
async def on_message(message):
    await bot.process_commands(message)

    if (status["read_msgs"] == False or
        message.author.bot or
        status["member_id"] != message.author.id or
        status["text_channel_id"] != message.channel.id):
        return

    # generate audio
    content = message.content
    if status["join_msg"] == True:
        status["join_msg"] = False
        content = "the TTS bot has joined the voice channel"

    vc = message.guild.voice_client
    # output to audio client
    if vc and vc.is_connected():
        if content == ";p":
            vc.pause()
            return
        elif content == ";r":
            vc.resume()
            return
        elif content == ";s":
            vc.stop()
            return

        process = subprocess.Popen(
                ["espeak-ng", content, "--stdout"],
                stdout=subprocess.PIPE
        )
        audio_source = discord.FFmpegPCMAudio(
                process.stdout,
                pipe=True,
                options=""
        )
        vc.play(audio_source)

    
# bind the bot to a certain user and channel
# TODO: i'm sure theres a better way to handle the default case
@bot.command()
async def listen(ctx, member: discord.Member = None, text_channel: discord.TextChannel = None):
    status["read_msgs"] = True

    if member == None:
        status["member_id"] = ctx.author.id
        display_member = ctx.author.name
    else:
        status["member_id"] = member.id
        display_member = member.name

    if text_channel == None:
        status["text_channel_id"] = ctx.channel.id
        display_channel = ctx.channel.name
    else:
        status["text_channel_id"] = text_channel.id
        display_channel = text_channel.name

    await ctx.send(f"Listening to user @{display_member} in text channel #{display_channel}")

@listen.error
async def listen_error(ctx, error):
    if isinstance(error, commands.BadArgument):
        await ctx.send("Either incorrect user mentioned or incorrect text channel mentioned.")
        await ctx.send("`Usage: @<bot> listen (@user)? (#text-channel)?`")

@bot.command()
async def unlisten(ctx):
  status = {
          "read_msgs": False,
          "join_msg": False,
          "member_id": None,
          "text_channel_id": None,
          "voice_channel_id": None,
  }


# have the bot join a channel
@bot.command()
async def join(ctx, voice_channel: discord.VoiceChannel):
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(voice_channel)
        await ctx.send(f"Moved to #!{voice_channel.name}")
        status["join_msg"] = True
    else:
        await voice_channel.connect()
        await ctx.send(f"Joined #!{voice_channel.name}")
        status["join_msg"] = True

@join.error
async def join_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("No voice channel mentioned.")
        await ctx.send("`Usage: @<bot> join #!voice-channel`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Incorrect voice channel mentioned.")
        await ctx.send("`Usage: @<bot> join #!voice-channel`")

@bot.command()
async def leave(ctx):
    vc = ctx.voice_client
    if vc is not None:
        await vc.disconnect()
        await ctx.send(f"Disconnected from #!{vc.channel.name}.")
    else:
        await ctx.send("Not currently in a voice channel.")

bot.run(secrets_data["discord_bot_token"])
