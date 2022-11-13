import random
import requests
import json
import ftx_functions
from guildlist import slash_guilds
from discord.ext import commands
from discord_slash import cog_ext, SlashContext


def get_current_price(pair):
    response = requests.get(f"https://ftx.com/api/markets/{pair}")
    data = json.loads(response.content)
    return float(data['result']['last'])


def get_fees():
    data = ftx_functions.get('account')
    return data['makerFee'], data['takerFee']


class Futures(commands.Cog):
    def __init__(self, client):
        self.client = client

    @cog_ext.cog_slash(name='fee', guild_ids=slash_guilds)
    async def fee(self, context: SlashContext, amount: str, pair: str):
        # parse amount
        if "k" in amount:
            amount = float(amount.replace("k", ""))
            amount *= 1000
        else:
            amount = float(amount)
        # Clean pair inputs
        suffix = '-PERP'
        pair = pair.upper()
        if not pair.endswith(suffix):
            pair = pair + suffix
        # ---
        maker, taker = get_fees()
        current_price = get_current_price(pair)
        usd_size = round(current_price * amount, 2)
        mfee = round(usd_size * maker, 2)
        tfee = round(usd_size * taker, 2)
        await context.send(f"""{pair}: **{current_price}** USD
{amount} {pair}: **{current_price * amount}** USD

Maker: **{mfee}** USD * 2 = **{mfee * 2}** USD ({round(maker * 100, 6)}%)
Taker: **{tfee}** USD * 2 = **{tfee * 2}** USD ({round(taker * 100, 6)}%)
Taker fee requires a **${round(tfee*2 / amount, 4)}** move to break even.""")

    @cog_ext.cog_slash(name='manualfee', guild_ids=slash_guilds)
    async def manualfee(self, context: SlashContext, usdvalue: str, feepercentage: float):
        if "k" in usdvalue:
            amount = float(usdvalue.replace("k", ""))
            amount *= 1000
        else:
            amount = float(usdvalue)

        fee = amount * feepercentage / 100
        await context.send(f"**{fee}** USD * 2 = **{fee * 2}** USD")

    @cog_ext.cog_slash(name='liquidation', guild_ids=slash_guilds)
    async def liquidation(self, context: SlashContext, leverage: float, pair: str):
        # Clean pair inputs
        suffix = '-PERP'
        pair = pair.upper()
        if not pair.endswith(suffix):
            pair = pair + suffix
        # ---
        current_price = get_current_price(pair)

        maintenance_margin_req = 0.006 if leverage > 20 else 0.03

        diff = current_price - current_price * (1 + maintenance_margin_req - (1 / leverage))

        msg = f"""**__Estimated__ Liquidations for {pair} (${current_price}) at {leverage}x leverage**
Move: {round(diff, 4)} USD move
Long: {round(current_price - diff, 4)} USD
Short: {round(current_price + diff, 4)} USD"""
        await context.send(msg)

    @cog_ext.cog_slash(name="randomposition", guild_ids=slash_guilds)
    async def randomposition(self, context: SlashContext):
        resp = ftx_functions.get("/markets")
        markets = []
        for market in resp:
            markets.append(market["name"])
        mkt = random.choice(markets)
        while "-PERP" not in mkt:
            mkt = random.choice(markets)
        await context.send(f"{random.choice(['Long', 'Short'])} ${random.randint(0, 4000)} on {mkt}")


def setup(client):
    client.add_cog(Futures(client))
