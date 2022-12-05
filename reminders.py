from datetime import datetime, timedelta

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import app_commands
from discord.ext import commands

from guildlist import slash_guilds

scheduler = AsyncIOScheduler()


async def send_reminder(channel, content: str) -> None:
    await channel.send(content)


class Reminders(commands.Cog):
    def __init__(self, client):
        self.client = client

    @app_commands.command(name="remindme", description="Set a reminder")
    async def remindme(self, interaction: discord.Interaction, days: int = 0, hours: int = 0, minutes: int = 0, message: str = None):
        reminder_time = datetime.now()
        reminder_time += timedelta(days=days, hours=hours, minutes=minutes)
        message = interaction.user.mention + " " + message
        scheduler.add_job(send_reminder, 'date', run_date=reminder_time, kwargs={"channel": interaction.channel, "content": message})
        await interaction.response.send_message(f"Scheduled reminder for {reminder_time.strftime('%b %-d %-I:%M %p')}.")
        if scheduler.state != 1:
            scheduler.start()


async def setup(client):
    await client.add_cog(Reminders(client), guilds=slash_guilds)
