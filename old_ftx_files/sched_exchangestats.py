import json
import os.path
import time

import discord
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord.ext import commands
from discord_slash import cog_ext, SlashContext

import ftx_functions
from guildlist import slash_guilds

scheduler = AsyncIOScheduler()


def get_data() -> dict:
    result = json.loads(requests.get("https://ftx.com/api/trade_stats").content)['result']
    result['timestamp'] = int(time.time())
    return result


def save_data(data: dict) -> None:
    data['price'] = ftx_functions.get("markets/BTC-PERP")['last']
    with open("exchange_stats.json", "r+") as file:
        fd = json.load(file)
        fd['data'].append(data)
        file.seek(0)
        json.dump(fd, file, indent=2)


def get_last_saved() -> dict:
    file = open("exchange_stats.json", "r")
    data = json.load(file)
    return data['data'][-1]


def get_buy_pct(data: dict, key: str) -> float:
    sellkey = key.replace("Buy", "Sell")
    return round(data[key] / (data[key] + data[sellkey]) * 100, 2)


async def send_embed(data, channel):
    old_takerbuypct = get_buy_pct(get_last_saved(), 'takerVolumeBuy')
    old_instbuypct = get_buy_pct(get_last_saved(), 'institutionVolumeBuy')
    old_retailbuypct = get_buy_pct(get_last_saved(), 'nonInstitutionVolumeBuy')
    takerbuypct = get_buy_pct(data, 'takerVolumeBuy')
    instbuypct = get_buy_pct(data, 'institutionVolumeBuy')
    retailbuypct = get_buy_pct(data, 'nonInstitutionVolumeBuy')

    embed = discord.Embed(title="FTX Exchange Stats Updated", color=0x00b4c9)
    embed.add_field(name="Taker Buy %", value=f"{old_takerbuypct} -> **{takerbuypct}**", inline=False)
    embed.add_field(name="Institution Buy %", value=f"{old_instbuypct} -> **{instbuypct}**", inline=True)
    embed.add_field(name="Retail Buy %", value=f"{old_retailbuypct} -> **{retailbuypct}**", inline=True)
    embed.set_thumbnail(url="https://help.ftx.com/hc/article_attachments/4410000944788/mceclip3.png")  # ftx logo
    last_update_mins = (time.time() - os.path.getmtime("exchange_stats.json")) / 60
    embed.set_footer(text=f"Update Interval: {int(last_update_mins)} mins")

    await channel.send(embed=embed)
    save_data(data)


def has_difference(data, data2):
    if get_buy_pct(data, 'takerVolumeBuy') != get_buy_pct(data2, 'takerVolumeBuy'):
        return True
    if get_buy_pct(data, 'institutionVolumeBuy') != get_buy_pct(data2, 'institutionVolumeBuy'):
        return True
    if get_buy_pct(data, 'nonInstitutionVolumeBuy') != get_buy_pct(data2, 'nonInstitutionVolumeBuy'):
        return True
    return False


class ExchangeStats(commands.Cog):
    def __init__(self, client):
        self.client = client
        scheduler.start()
        scheduler.add_job(self.scheduled_update, 'interval', minutes=1, args=[self])

    async def scheduled_update(*args):
        if len(args) > 0:
            data = get_data()
            if has_difference(data, get_last_saved()):
                await send_embed(data, args[0].client.get_channel(831064380242133002))

    @cog_ext.cog_slash(name='forceupdateexchangestats', guild_ids=slash_guilds)
    async def forceupdateexchangestats(self, context: SlashContext):
        data = get_data()
        await send_embed(data, context)


def setup(client):
    client.add_cog(ExchangeStats(client))
