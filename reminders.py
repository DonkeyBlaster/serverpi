from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from discord_slash import cog_ext, SlashContext

from guildlist import slash_guilds

scheduler = AsyncIOScheduler()


async def send_reminder(channel, content: str) -> None:
    await channel.send(content)


class Reminders(commands.Cog):
    def __init__(self, client):
        self.client = client

    @cog_ext.cog_slash(name="remindme", guild_ids=slash_guilds)
    async def remindme(self, context: SlashContext, days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0, message: str = None):
        reminder_time = datetime.now()
        reminder_time += timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
        message = context.author.mention + " " + message
        scheduler.add_job(send_reminder, 'date', run_date=reminder_time, kwargs={"channel": context.channel, "content": message})
        await context.reply(f"Scheduled reminder for {reminder_time.strftime('%b %-d %-I:%M %p')}.")
        if scheduler.state != 1:
            scheduler.start()


def setup(client):
    client.add_cog(Reminders(client))
