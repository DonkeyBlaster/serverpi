import json
import re
import subprocess

import discord
import requests
from discord.ext import commands


def get_usd_cad_conversion():
    return float(
        json.loads(requests.get("https://api.coinbase.com/v2/exchange-rates", params={"currency": "USD"}).content)[
            'data']['rates']['CAD'])


def parse_price(price_input):
    price_input = price_input.lower()
    try:
        amt = float(re.findall(r"\d+\.?\d*", price_input)[0])
        if "k" in price_input:
            amt *= 1000

        return amt

    except IndexError or ValueError:
        return None


class ChatHandler(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.restarts = 0

    @commands.Cog.listener()
    async def on_message(self, message):
        msgc: str = message.content.lower()

        if msgc == "auto restart price bots" and message.author.id == 636013327276965889:
            try:
                pipe = subprocess.Popen("sudo service crypto-price-bots restart", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                out, err = pipe.communicate()
                response = out.decode()
                error = err.decode()
                combined = response + error
                if combined == "":
                    self.restarts += 1
                    await message.reply(f"price bots restarted, count {self.restarts} from <t:1645736104>")
                    # await message.delete()
                else:
                    await message.reply(f"```{combined}```")
            except discord.errors.HTTPException as _e:
                await message.reply(str(_e))

        # price conversion parsing
        if msgc.endswith("to usd"):
            await message.reply(f"${round(parse_price(message.content) / get_usd_cad_conversion(), 2)} USD")
        elif msgc.endswith("to cad"):
            await message.reply(f"${round(parse_price(message.content) * get_usd_cad_conversion(), 2)} CAD")


def setup(client):
    client.add_cog(ChatHandler(client))
