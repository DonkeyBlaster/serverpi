import asyncio
import os
import random
import subprocess
import time
from typing import List

import discord
from discord import app_commands
from discord import ui
from discord.ext import commands
from discord.ext.commands import Bot
from dotenv import load_dotenv

from guildlist import slash_guilds

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
delete_cooldown = 2

startup_extensions = ["chathandler", "sched_feargreed", "reminders"]
client = Bot(intents=discord.Intents.all(), command_prefix='!')


@client.event
async def on_ready():
    for extension in startup_extensions:
        try:
            await client.load_extension(extension)
            print(f"Extension {extension} loaded")
        except Exception as e:
            print(e)
    for guild in slash_guilds:
        await client.tree.sync(guild=discord.Object(id=guild))
        print("Synced slash commands for guild " + str(guild))
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.hybrid_command(name='ping')
@app_commands.guilds(*slash_guilds)
async def ping(context):
    beforeping = time.monotonic()
    messageping = await context.send("Pong!")
    pingtime = (time.monotonic() - beforeping) * 1000
    await messageping.edit(content=f"""Pong!
REST API: `{int(pingtime)}ms`
WS API Heartbeat: `{int(client.latency * 1000)}ms`""")


async def extensions_autocomplete(
        interaction: discord.Interaction,
        current: str
) -> List[app_commands.Choice[str]]:
    return [
        app_commands.Choice(name=extension, value=extension)
        for extension in startup_extensions if current.lower() in extension.lower()
    ]


@client.hybrid_group(name="extensions")
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def extensions(context):
    pass


@extensions.command(name='load')
@app_commands.autocomplete(extension=extensions_autocomplete)
async def load(context, extension):
    try:
        await client.load_extension(extension)
        msg = await context.send(f"Extension `{extension}` loaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await context.send(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await context.send("Error exceeds 2000 characters. See console for details.")


@extensions.command(name='unload')
@app_commands.autocomplete(extension=extensions_autocomplete)
async def unload(context, extension):
    await client.unload_extension(extension)
    msg = await context.send(f"Extension `{extension}` unloaded.")
    await asyncio.sleep(delete_cooldown)
    await msg.delete()


@extensions.command(name='reload')
@app_commands.autocomplete(extension=extensions_autocomplete)
async def reload(context, extension):
    try:
        await client.unload_extension(extension)
        await client.load_extension(extension)
        msg = await context.send(f"Extension `{extension}` reloaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await context.send(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await context.send("Error exceeds 2000 characters. See console for details.")


class VoteKickView(ui.View):
    def __init__(self):
        super().__init__()

    @ui.button(label="F1", style=discord.ButtonStyle.green)
    async def f1(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in client.votekick_f1 or interaction.user in client.votekick_f2:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
        else:
            await interaction.response.defer()
            client.votekick_f1.append(interaction.user)
            await handle_button_press()

    @ui.button(label="F2", style=discord.ButtonStyle.red)
    async def f2(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in client.votekick_f1 or interaction.user in client.votekick_f2:
            await interaction.response.send_message("You have already voted.", ephemeral=True)
        else:
            await interaction.response.defer()
            client.votekick_f2.append(interaction.user)
            await handle_button_press()


async def handle_button_press():
    voting_done = False
    to_kick = False
    lenf1 = len(client.votekick_f1)
    lenf2 = len(client.votekick_f2)

    if lenf1 + lenf2 >= len(client.votekick_author.voice.channel.members):  # if everyone voted
        if lenf1 >= (lenf1 + lenf2 - 1):  # if those that voted f1 are all but the kickee, kick
            to_kick = True
            voting_done = True
        else:
            to_kick = False
    if lenf2 > 1:  # if anyone other than the kickee voted no, just in like in cs, don't kick
        to_kick = False
        voting_done = True

    if voting_done:
        if to_kick:
            embededit = discord.Embed(title="Vote Passed!", color=0x00ff00)
            embededit.add_field(name="Kicking user...", value=client.votekick_target.mention, inline=False)
            await client.votekick_target.move_to(None)
        elif not to_kick:
            embededit = discord.Embed(title="Vote Failed.", color=0xff0000)
            embededit.add_field(name="Kick failed:", value="Not enough users voted.", inline=False)

    elif not voting_done:  # if voting is not done, display updated vote count
        embededit = discord.Embed(title=f"Vote by: {client.votekick_author}", color=0xc6c6c6)
        embededit.add_field(name="Kick user:", value=client.votekick_target.mention, inline=False)
        embededit.set_footer(text=f"Yes: {lenf1} | No: {lenf2}")

    client.votekick_msg = await client.votekick_msg.edit(embed=embededit, view=VoteKickView())


@client.hybrid_command(name='votekick')
@app_commands.guilds(*slash_guilds)
async def votekick(context, target: discord.Member):
    if context.author.voice:
        if target.voice.channel == context.author.voice.channel:
            # autovotes like csgo
            client.votekick_f1 = [context.author]
            client.votekick_f2 = [target]
            client.votekick_author = context.author
            client.votekick_target = target

            embed = discord.Embed(title=f"Vote by: {client.votekick_author}", color=0xc6c6c6)
            embed.add_field(name="Kick user:", value=client.votekick_target.mention, inline=False)
            embed.set_footer(text="Yes: 1 | No: 1")
            client.votekick_msg = await context.send(embed=embed, view=VoteKickView())

            await handle_button_press()  # handle initial autovotes
        else:
            await context.send(content="The specified user is not in your VC.", hidden=True)
    else:
        await context.send(content="You must be in a VC to use this.", hidden=True)


@client.hybrid_command(name='shell')
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def shell(context, *, command: str):
    check = discord.utils.get(context.guild.emojis, name="checkmark")
    try:
        pipe = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pipe.communicate()
        error = err.decode()
        response = out.decode()
        combined = response + error
        if combined == "":
            await context.send(f"{check} Command executed with no output.")
        else:
            await context.send(f"```{combined}```")
    except discord.errors.HTTPException as _e:
        await context.send(_e)


@client.hybrid_command(name='cryptopricebotsrestart')
@app_commands.guilds(*slash_guilds)
async def cryptopricebotsrestart(context):
    check = discord.utils.get(context.guild.emojis, name="checkmark")
    try:
        pipe = subprocess.Popen("sudo service crypto-price-bots restart", shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = pipe.communicate()
        response = out.decode()
        error = err.decode()
        combined = response + error
        if combined == "":
            msg = await context.send(f"{check} Price bots restarted.")
            await asyncio.sleep(delete_cooldown)
            await msg.delete()
        else:
            await context.send(f"```{combined}```")
    except discord.errors.HTTPException as _e:
        await context.send(str(_e))


@client.hybrid_command(name='purge')
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def purge(context, number: int = None):
    if number is None or number > 100:
        await context.send(f"{context.author.mention} :x: Maximum 100 messages.", hidden=True)
    else:
        client.deleted_messages = []
        async for message in context.channel.history(
                limit=number):  # number+1 was removed because the slashcommand doesn't count as a message
            client.deleted_messages.append(message)
        client.deleted_messages.reverse()
        await context.channel.delete_messages(client.deleted_messages)
        msg = await context.send(f"Deleted {number} messages.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()


@client.hybrid_command(name='unpurge')
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def restore(context, number: int = 0):
    if number > 100:
        await context.send(f"{context.author.mention} :x: Maximum 100 messages.", hidden=True)
    elif number == 0 and client.deleted_messages is not None:
        color = 0x2f3136
        for message in client.deleted_messages:
            # Check if message has content
            embed = discord.Embed(description="No Message Content",
                                  color=color) if not message.content else discord.Embed(description=message.content,
                                                                                         color=color)
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)
            # Check if message has attachments
            if message.attachments:
                for i in message.attachments:
                    embed.add_field(name="Attachment", value=i.url)
            await context.channel.send(embed=embed)
    else:
        color = 0x2f3136
        for i in range(number):
            message = client.deleted_messages[i]
            embed = discord.Embed(description="No Message Content",
                                  color=color) if not message.content else discord.Embed(description=message.content,
                                                                                         color=color)
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)
            # Check if message has attachments
            if message.attachments:
                for j in message.attachments:
                    embed.add_field(name="Attachment", value=j.url)
            await context.channel.send(embed=embed)
    m = await context.reply("Restored messages.")
    await asyncio.sleep(delete_cooldown)
    await m.delete()


@client.hybrid_command(name='coin')
@app_commands.guilds(*slash_guilds)
async def coin(context):
    """Flips a coin."""
    await context.send(random.choice(["Heads", "Tails"]))


@client.hybrid_command(name='temps')
@app_commands.guilds(*slash_guilds)
async def temps(context):
    pipe = subprocess.Popen("ssh pi@serverpi1 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi1 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi2 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi2 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi3 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi3 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi4 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi4 = response + error

    await context.send(
        f"serverpi1: `{serverpi1}`\nserverpi2: `{serverpi2}`\nserverpi3: `{serverpi3}`\nserverpi4: `{serverpi4}`")


@client.hybrid_command(name="restart")
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def restart(context):
    m = await context.reply(":white_check_mark:")
    await m.delete()
    subprocess.Popen("sudo service serverpi restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@client.hybrid_command(name="update")
@app_commands.guilds(*slash_guilds)
@commands.is_owner()
async def update(context):
    await context.add_reaction("🔄")
    pipe = subprocess.Popen("git pull", shell=True, stdout=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    combined = response + error
    await context.send(f"```{combined}```")
    if error is None:
        await context.send("Restarting...")
        subprocess.Popen("sudo service serverpi restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    else:
        await context.send("Error while updating, not restarting.")

client.run(TOKEN)
