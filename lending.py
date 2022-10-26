import asyncio
from discord_slash.utils.manage_components import create_button, create_actionrow, wait_for_component
import main
import ftx_functions
from guildlist import slash_guilds
from discord.ext import commands
from discord_slash import cog_ext, SlashContext, ButtonStyle, ComponentContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

scheduler = AsyncIOScheduler()


class Lending(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def cancel_all_lending_offers(self):
        response = ftx_functions.post("spot_margin/offers", params={"coin": "USD", "size": "0", "rate": "1e-6"})
        if response is None:
            await self.client.futures_channel.send("Active USD lending offers cancelled.")
        return False

    @cog_ext.cog_slash(name='scheduleunlend', guild_ids=slash_guilds)
    @commands.is_owner()
    async def scheduleunlend(self, context: SlashContext, hours: float):
        if hours == 0:
            await self.cancel_all_lending_offers()
            await context.reply("Cancelled active USD lending offers.")
        else:
            cancel_time = datetime.now() + timedelta(hours=hours)
            scheduler.add_job(self.cancel_all_lending_offers, 'date', run_date=cancel_time)
            if scheduler.state != 1:
                scheduler.start()
            formatted_time = cancel_time.strftime("%I:%M %p")
            buttons = [create_button(style=ButtonStyle.blue, label="Ok"),
                       create_button(style=ButtonStyle.blue, label="Dismiss"),
                       create_button(style=ButtonStyle.red, label="Cancel")]
            action_row = create_actionrow(*buttons)
            msg = await context.reply(f"Cancelling active USD lending offers at {formatted_time}.", components=[action_row])
            button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row, check=main.check_owner)
            await msg.edit(components=[])

            # We don't have a case for "Ok" since all that should do is remove the buttons, which is handled above
            if button_ctx.component['label'] == "Dismiss":
                await self.client.futures_channel.send(msg.content)
                await msg.delete()
            elif button_ctx.component['label'] == "Cancel":
                scheduler.shutdown()
                scheduler.remove_all_jobs()
                msg2 = await button_ctx.reply("Cancelled.")
                await asyncio.sleep(main.delete_cooldown)
                await msg.delete()
                await msg2.delete()

    @cog_ext.cog_slash(name="lendalts", guild_ids=slash_guilds)
    @commands.is_owner()
    async def lendalts(self, context: SlashContext, excluded: str = ""):
        # First, we get all balances and exclude FTT and USD because staking/collat
        all_tokens = ftx_functions.get("wallet/balances")
        tokens = []
        excluded_tokens = ['USD', 'FTT']
        for token in all_tokens:
            if token['total'] > 0 and token['coin'] not in excluded_tokens and token['coin'] != excluded.upper():
                tokens.append(token)

        print(tokens)

        to_lend = {}
        for token_json in tokens:
            if token_json['availableWithoutBorrow'] > 0:
                to_lend[token_json['coin']] = token_json['total']

        strmsg = "**Tokens available to lend:**"

        for token_set in to_lend:
            strmsg += f"\n - {token_set}: {to_lend[token_set]}"

        buttons = [create_button(style=ButtonStyle.green, label="Lend all"),
                   create_button(style=ButtonStyle.red, label="Cancel")]
        action_row = create_actionrow(*buttons)
        msg = await context.reply(strmsg, components=[action_row])

        button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row, check=main.check_owner)
        await msg.edit(components=[])

        if button_ctx.component['label'] == "Lend all":
            lendstr = ""
            lendmsg = None
            for lendable_token in to_lend:
                response = ftx_functions.post("spot_margin/offers", params={"coin": lendable_token, "size": to_lend[lendable_token], "rate": "1e-6"})
                if response is None:
                    lendstr += f"Successfully lent {to_lend[lendable_token]} {lendable_token}.\n"
                else:
                    lendstr += response

                if lendmsg is None:
                    lendmsg = await context.reply(lendstr)
                else:
                    await lendmsg.edit(content=lendstr)

            await self.client.futures_channel.send(msg.content + "\n__The above tokens have been lent.__")
            await button_ctx.defer(ignore=True)

        elif button_ctx.component['label'] == "Cancel":
            msg2 = await button_ctx.reply("Cancelled.")
            await asyncio.sleep(main.delete_cooldown)
            await msg.delete()
            await msg2.delete()


def setup(client):
    client.add_cog(Lending(client))
