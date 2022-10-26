import asyncio
import subprocess
import random
import discord
import time
import ftx_positionmanager
import ftx_ws
from guildlist import slash_guilds
from discord.ext import commands
from discord.ext.commands import Bot
from discord_slash import SlashCommand, SlashContext, ComponentContext
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
from discord_slash.utils.manage_commands import create_choice, create_option
from discord_slash.model import ButtonStyle

TOKEN = open('token.txt', 'r').read()
delete_cooldown = 2

startup_extensions = ["futures", "staking", "lending", "chathandler", "sched_feargreed", "sched_exchangestats", "reminders"]
cog_choices = []
for extstr in startup_extensions:
    cog_choices.append(create_choice(name=extstr, value=extstr))
ext_options = [create_option(name="ext", description="The cog to interact with", option_type=3, required=True, choices=cog_choices)]

client = Bot(intents=discord.Intents.all(), command_prefix=' ')
slash = SlashCommand(client, sync_commands=True, sync_on_cog_reload=True)


def check_owner(cctx: ComponentContext):
    return cctx.author_id == 291661685863874560


@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    client.futures_channel = client.get_channel(831064380242133002)
    client.notify_next_fill = True
    await ftx_ws.main_loop(client)


@slash.slash(name='ping', guild_ids=slash_guilds)
async def ping(context: SlashContext):
    beforeping = time.monotonic()
    messageping = await context.send("Pong!")
    pingtime = (time.monotonic() - beforeping) * 1000
    await messageping.edit(content=f"""Pong!
REST API: `{int(pingtime)}ms`
WS API Heartbeat: `{int(client.latency * 1000)}ms`""")


@slash.slash(name='load', guild_ids=slash_guilds, options=ext_options)
@commands.is_owner()
async def load(context: SlashContext, ext):
    try:
        client.load_extension(ext)
        msg = await context.send(f"Extension `{ext}` loaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await context.send(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await context.send("Error exceeds 2000 characters. See console for details.")


@slash.slash(name='unload', guild_ids=slash_guilds, options=ext_options)
@commands.is_owner()
async def unload(context: SlashContext, ext):
    client.unload_extension(ext)
    msg = await context.send(f"Extension `{ext}` unloaded.")
    await asyncio.sleep(delete_cooldown)
    await msg.delete()


@slash.slash(name='reload', guild_ids=slash_guilds, options=ext_options)
@commands.is_owner()
async def reload(context: SlashContext, ext):
    try:
        client.unload_extension(ext)
        client.load_extension(ext)
        msg = await context.send(f"Extension `{ext}` reloaded.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    except Exception as _e:
        try:
            await context.send(str(_e))
        except discord.errors.HTTPException as _e:
            print(_e)
            await context.send("Error exceeds 2000 characters. See console for details.")


@slash.slash(name='votekick', guild_ids=slash_guilds)
async def votekick(context: SlashContext, member: discord.Member):
    if context.author.voice:
        if member.voice.channel == context.author.voice.channel:
            processed = False
            to_kick = False
            f1 = []
            f2 = []
            # autovotes like csgo
            f1.append(context.author)
            f2.append(member)
            # --
            embed = discord.Embed(title=f"Vote by: {context.author.display_name}", color=0xc6c6c6)
            embed.add_field(name="Kick user:", value=member.mention, inline=False)
            embed.set_footer(text="Yes: 1 | No: 1")
            buttons = [create_button(style=ButtonStyle.green, label="F1"),
                       create_button(style=ButtonStyle.red, label="F2")]
            action_row = create_actionrow(*buttons)
            msg = await context.send(embed=embed, components=[action_row])
            while not processed:
                button_ctx: ComponentContext = await wait_for_component(client, components=action_row)
                if button_ctx.author not in f1 and button_ctx.author not in f2:  # if author has not voted already
                    embed = discord.Embed(title=f"Vote by: {context.author.display_name}", color=0xc6c6c6)
                    embed.add_field(name="Kick user:", value=member.mention, inline=False)
                    if button_ctx.component['label'] == 'F1':
                        f1.append(button_ctx.author)
                    elif button_ctx.component['label'] == 'F2':
                        f2.append(button_ctx.author)
                    embed.set_footer(text=f"Yes: {len(f1)} | No: {len(f2)}")
                    await button_ctx.edit_origin(embed=embed)
                else:
                    await button_ctx.send("You've already voted on this kick.", hidden=True)

                if len(f1) + len(f2) >= len(context.author.voice.channel.members):
                    if len(f1) >= (len(f1) + len(f2) - 1):  # if those that voted f1 are all but the kickee, kick
                        to_kick = True
                    else:  # else dont kick
                        to_kick = False
                    if len(f2) != 1:  # if anyone other than the kickee voted no, just in like in cs, don't kick
                        to_kick = False
                    processed = True

            embededit = None
            if not to_kick:
                embededit = discord.Embed(title="Vote Failed.", color=0xff0000)
                embededit.add_field(name="Kick failed:", value="Not enough users voted.", inline=False)
            elif to_kick:
                embededit = discord.Embed(title="Vote Passed!", color=0x00ff00)
                embededit.add_field(name="Kicking user...", value=member.mention, inline=False)
                await member.move_to(None)
            await msg.edit(embed=embededit, components=None)

        else:
            await context.send(content="The specified user is not in your VC.", hidden=True)
    else:
        await context.send(content="You must be in a VC to use this.", hidden=True)


@slash.slash(name='shell', guild_ids=slash_guilds)
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


@slash.slash(name='cryptopricebotsrestart', guild_ids=slash_guilds)
async def cryptopricebotsrestart(context: SlashContext):
    check = discord.utils.get(context.guild.emojis, name="checkmark")
    try:
        pipe = subprocess.Popen("sudo service crypto-price-bots restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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


@slash.slash(name='purge', guild_ids=slash_guilds)
@commands.is_owner()
async def purge(context, number: int = None):
    if number is None or number > 100:
        await context.send(f"{context.author.mention} :x: Maximum 100 messages.", hidden=True)
    else:
        client.deleted_messages = []
        async for message in context.channel.history(limit=number):  # number+1 was removed because the slashcommand doesn't count as a message
            client.deleted_messages.append(message)
        client.deleted_messages.reverse()
        await context.channel.delete_messages(client.deleted_messages)
        msg = await context.send(f"Deleted {number} messages.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()


@slash.slash(name='unpurge', guild_ids=slash_guilds)
@commands.is_owner()
async def restore(context, number: int = 0):
    if number > 100:
        await context.send(f"{context.author.mention} :x: Maximum 100 messages.", hidden=True)
    elif number == 0 and client.deleted_messages is not None:
        color = 0x2f3136
        for message in client.deleted_messages:
            # Check if message has content
            embed = discord.Embed(description="No Message Content", color=color) if not message.content else discord.Embed(description=message.content, color=color)
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
            embed = discord.Embed(description="No Message Content", color=color) if not message.content else discord.Embed(description=message.content, color=color)
            embed.set_author(name=message.author, icon_url=message.author.avatar_url)
            # Check if message has attachments
            if message.attachments:
                for i in message.attachments:
                    embed.add_field(name="Attachment", value=i.url)
            await context.channel.send(embed=embed)
    m = await context.reply("Restored messages.")
    await asyncio.sleep(delete_cooldown)
    await m.delete()


@slash.slash(name='coin', guild_ids=slash_guilds)
async def coin(context: SlashContext):
    await context.send(random.choice(["Heads", "Tails"]))


@slash.slash(name='temps', guild_ids=slash_guilds)
async def temps(context: SlashContext):
    pipe = subprocess.Popen("ssh pi@serverpi1 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi1 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi2 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi2 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi3 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi3 = response + error

    pipe = subprocess.Popen("ssh pi@serverpi4 vcgencmd measure_temp", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    serverpi4 = response + error

    await context.send(f"serverpi1: `{serverpi1}`\nserverpi2: `{serverpi2}`\nserverpi3: `{serverpi3}`\nserverpi4: `{serverpi4}`")


@slash.slash(name="restart", guild_ids=slash_guilds)
@commands.is_owner()
async def restart(context: SlashContext):
    m = await context.reply(":white_check_mark:")
    await m.delete()
    subprocess.Popen("sudo service serverpi restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@slash.slash(name="lcdreset", guild_ids=slash_guilds)
async def lcdreset(context: SlashContext):
    pipe = subprocess.Popen("ssh pi@serverpi4 sudo service crypto-prices restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = pipe.communicate()
    response = out.decode()
    error = err.decode()
    combined = response + error
    if combined == "":
        check = discord.utils.get(context.guild.emojis, name="checkmark")
        msg = await context.reply(f"{check} LCD display reset.")
        await asyncio.sleep(delete_cooldown)
        await msg.delete()
    else:
        await context.reply(combined)


@slash.slash(name="updatepositions", guild_ids=slash_guilds)
@commands.is_owner()
async def updatepositions(context: SlashContext):
    ftx_positionmanager.update_positions()
    await context.reply(str(ftx_positionmanager.get_all_raw_positions()))


@slash.slash(name="printpositions", guild_ids=slash_guilds)
@commands.is_owner()
async def printpositions(context: SlashContext):
    await context.reply(str(ftx_positionmanager.get_all_raw_positions()))


@slash.slash(name="notifyonnextfill", guild_ids=slash_guilds)
@commands.is_owner()
async def notifyonnextfill(context: SlashContext):
    client.notify_next_fill = True
    m = await context.reply(":white_check_mark:")
    await asyncio.sleep(delete_cooldown)
    await m.delete()


for extension in startup_extensions:
    try:
        client.load_extension(extension)
        print(f"Extension {extension} loaded")
    except Exception as e:
        print(e)

client.run(TOKEN)
