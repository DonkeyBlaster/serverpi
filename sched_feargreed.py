import json

import discord
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import app_commands
from discord.ext import commands

from guildlist import slash_guilds

scheduler = AsyncIOScheduler()


def get_name_string():
    response = requests.get("https://api.alternative.me/fng/")
    data = json.loads(response.content)
    value = data['data'][0]['value']
    classification = data['data'][0]['value_classification']
    return f"{value} / {classification}"


async def update_role_name(client, name_string):
    guild = client.get_guild(696082479752413274)
    role = guild.get_role(839669817463013397)
    await role.edit(name=name_string)


class FearGreed(commands.Cog):
    def __init__(self, client):
        self.client = client
        scheduler.start()
        scheduler.add_job(self.scheduled_update, 'cron', hour=16, minute=1, args=[self])

    async def scheduled_update(*args):
        if len(args) > 0:
            client = args[0].client
            name_string = get_name_string()
            await update_role_name(client, name_string)
            channel = client.get_channel(696082479752413277)
            await channel.send(f"Updated F&G to {name_string}")

    @app_commands.command(name='forceupdaterolename', description='Force update the F&G role name')
    async def forceupdaterolename(self, interaction: discord.Interaction):
        name_string = get_name_string()
        await update_role_name(self.client, name_string)
        await interaction.response.send_message(f"Updated role name to {name_string}")


async def setup(client):
    await client.add_cog(FearGreed(client), guilds=slash_guilds)
