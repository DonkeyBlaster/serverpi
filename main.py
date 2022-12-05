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

from guildlist import slash_guilds, guild_ids

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
delete_cooldown = 2

startup_extensions = ["chathandler", "sched_feargreed", "reminders"]
client = Bot(intents=discord.Intents.all(), command_prefix=' ')


@client.event
async def on_ready():
    for extension in startup_extensions:
        try:
            await client.load_extension(extension)
            print(f"Extension {extension} loaded")
        except Exception as e:
            print(e)
    for id in guild_ids:
        await client.tree.sync(guild=discord.Object(id=id))
        print("Synced slash commands for guild " + str(id))
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')


@client.tree.command(name='ping', description="Returns the bot's ping", guilds=slash_guilds)
async def ping(interaction: discord.Interaction):
    beforeping = time.monotonic()
    await interaction.response.send_message("Pong!")
    pingtime = (time.monotonic() - beforeping) * 1000
    await interaction.edit_original_response(content=f"""Bing bing bong bong bing bing bing
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


extensions = app_commands.Group(name="extensions", description="Extension management")


@extensions.command(name='load', description="Loads the given extension")
@app_commands.autocomplete(extension=extensions_autocomplete)
@commands.is_owner()
async def load(interaction: discord.Interaction, extension: str):
    try:
        await client.load_extension(extension)
        msg = await interaction.response.send_message(f"Extension `{extension}` loaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await interaction.response.send_message(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await interaction.response.send_message("Error exceeds 2000 characters. See console for details.")


@extensions.command(name='unload', description="Unloads the given extension")
@app_commands.autocomplete(extension=extensions_autocomplete)
@commands.is_owner()
async def unload(interaction: discord.Interaction, extension: str):
    await client.unload_extension(extension)
    msg = await interaction.response.send_message(f"Extension `{extension}` unloaded.")
    await asyncio.sleep(delete_cooldown)
    await msg.delete()


@extensions.command(name='reload', description="Reloads the given extension")
@app_commands.autocomplete(extension=extensions_autocomplete)
@commands.is_owner()
async def reload(interaction: discord.Interaction, extension: str):
    try:
        await client.unload_extension(extension)
        await client.load_extension(extension)
        msg = await interaction.response.send_message(f"Extension `{extension}` reloaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await interaction.response.send_message(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await interaction.response.send_message("Error exceeds 2000 characters. See console for details.")

client.tree.add_command(extensions, guilds=slash_guilds)


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


@client.tree.command(name='shell', description="Runs a bash command on the server", guilds=slash_guilds)
@commands.is_owner()
async def shell(interaction: discord.Interaction, *, command: str):
    await interaction.response.defer()
    check = discord.utils.get(interaction.guild.emojis, name="checkmark")
    try:
        pipe = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = pipe.communicate()
        error = err.decode()
        response = out.decode()
        combined = response + error
        if combined == "":
            await interaction.followup.send(f"{check} Command executed with no output.")
        else:
            await interaction.followup.send(f"```{combined}```")
    except discord.errors.HTTPException as _e:
        await interaction.followup.send(_e)


@client.tree.command(name='cryptopricebotsrestart', description="Restarts (some of) the crypto price bots", guilds=slash_guilds)
async def cryptopricebotsrestart(interaction: discord.Interaction):
    check = discord.utils.get(interaction.guild.emojis, name="checkmark")
    try:
        pipe = subprocess.Popen("sudo service crypto-price-bots restart", shell=True, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = pipe.communicate()
        response = out.decode()
        error = err.decode()
        combined = response + error
        if combined == "":
            msg = await interaction.response.send_message(f"{check} Price bots restarted.")
            await asyncio.sleep(delete_cooldown)
            await msg.delete()
        else:
            await interaction.response.send_message(f"```{combined}```")
    except discord.errors.HTTPException as _e:
        await interaction.response.send_message(str(_e))


@client.tree.command(name='purge', description="Purges a specified number of messages", guilds=slash_guilds)
@commands.is_owner()
async def purge(interaction: discord.Interaction, number: int = None):
    await interaction.response.defer()
    if number is None or number > 100:
        await interaction.response.send_message(f"{interaction.user.mention} :x: Maximum 100 messages.", hidden=True)
    else:
        client.deleted_messages = []

        skipped_first: bool = False
        async for message in interaction.channel.history(limit=number+1):  # +1 to include the command message
            if not skipped_first:
                skipped_first = True
                continue
            client.deleted_messages.append(message)

        client.deleted_messages.reverse()
        await interaction.channel.delete_messages(client.deleted_messages)
        await interaction.followup.send(f"Deleted {number} messages.")
        await asyncio.sleep(delete_cooldown)
        await interaction.delete_original_response()


@client.tree.command(name='unpurge', description="Unpurges all previously deleted messages", guilds=slash_guilds)
@commands.is_owner()
async def unpurge(interaction: discord.Interaction):
    color = 0x2f3136
    await interaction.response.defer()

    for message in client.deleted_messages:
        # Check if message has content
        embed = discord.Embed(description="No Message Content",
                              color=color) if not message.content else discord.Embed(description=message.content,
                                                                                     color=color)
        embed.set_author(name=message.author, icon_url=message.author.avatar)
        # Check if message has attachments
        if message.attachments:
            for i in message.attachments:
                embed.add_field(name="Attachment", value=i.url)
        await interaction.channel.send(embed=embed)

    m = await interaction.followup.send("Restored messages.")
    await asyncio.sleep(delete_cooldown)
    await m.delete()


@client.tree.command(name='coin', description="Flips a coin", guilds=slash_guilds)
async def coin(interaction: discord.Interaction):
    await interaction.response.send_message(random.choice(["Heads", "Tails"]))


@client.tree.command(name='temps', description="Gets the current temperature of the serverpis", guilds=slash_guilds)
async def temps(interaction: discord.Interaction):
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

    await interaction.response.send_message(f"""serverpi1: `{serverpi1}`
serverpi2: `{serverpi2}`
serverpi3: `{serverpi3}`""")


@client.tree.command(name="restart", description="Restarts the bot", guilds=slash_guilds)
@commands.is_owner()
async def restart(interactions: discord.Interaction):
    await interactions.response.send_message(":white_check_mark:")
    await asyncio.sleep(0.2)
    await interactions.delete_original_response()
    subprocess.Popen("sudo service serverpi restart", shell=True)


@client.tree.command(name="update", description="Pulls from the GitHub Repository and restarts the bot", guilds=slash_guilds)
@commands.is_owner()
async def update(interaction: discord.Interaction):
    await interaction.response.defer()
    pipe = subprocess.Popen("git pull", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    combined = response + error
    await interaction.response.send_message(f"```{combined}```")
    if response == "Already up to date.":
        await interaction.followup.send("No update available.")
    elif error == "":
        await interaction.followup.send("Restarting...")
        subprocess.Popen("sudo service serverpi restart", shell=True)
    else:
        await interaction.followup.send("Error while updating, not restarting.")

client.run(TOKEN)
