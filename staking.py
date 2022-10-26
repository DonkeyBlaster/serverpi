import asyncio
from discord_slash.utils.manage_components import create_button, wait_for_component, create_actionrow
import ftx_functions
import main
from guildlist import slash_guilds
from discord.ext import commands
from discord_slash import cog_ext, SlashContext, ButtonStyle, ComponentContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

staking_interval = 60


def get_stakable_solana():
    balances = ftx_functions.get("wallet/balances")
    for coin in balances:
        if coin['coin'] == "SOL":
            return float(coin['free'])


def stake_all_solana():
    avail_sol = get_stakable_solana()
    ftx_functions.post("srm_stakes/stakes", {"coin": "SOL", "size": avail_sol})


class Staking(commands.Cog):
    def __init__(self, client):
        self.client = client

    @cog_ext.cog_slash(name='enableautostaking', guild_ids=slash_guilds)
    @commands.is_owner()
    async def enableautostaking(self, context: SlashContext):
        avail_sol = get_stakable_solana()
        scheduler.add_job(stake_all_solana, 'interval', minutes=staking_interval)
        if avail_sol != 0:
            buttons = [create_button(style=ButtonStyle.green, label="Yes"),
                       create_button(style=ButtonStyle.blue, label="Proceed without staking"),
                       create_button(style=ButtonStyle.red, label="Cancel")]
            action_row = create_actionrow(*buttons)
            msg = await context.reply(f"{avail_sol} Solana available. Stake immediately and start auto-staking?", components=[action_row])
            button_ctx: ComponentContext = await wait_for_component(self.client, components=action_row, check=main.check_owner)
            await msg.edit(components=None)

            if button_ctx.component['label'] == "Yes":
                stake_all_solana()
                rtn = scheduler.start()
                if rtn is None:
                    await button_ctx.reply("Available Solana staked; auto-staking started.")
                else:
                    await button_ctx.reply(rtn)
            elif button_ctx.component['label'] == "Proceed without staking":
                rtn = scheduler.start()
                if rtn is None:
                    await button_ctx.reply(f"Proceeding without staking, next stake in {staking_interval} minutes.")
                else:
                    await button_ctx.reply(rtn)
            elif button_ctx.component['label'] == "Cancel":
                msg2 = await button_ctx.reply("Cancelled.")
                await asyncio.sleep(main.delete_cooldown)
                await msg.delete()
                await msg2.delete()
        else:
            rtn = scheduler.start()
            if rtn is None:
                await context.reply(f"Proceeding without staking, next stake in {staking_interval} minutes.")
            else:
                await context.reply(rtn)

    @cog_ext.cog_slash(name='autostakingstatus', guild_ids=slash_guilds)
    async def autostakingstatus(self, context: SlashContext):
        if scheduler.state == 0:
            await context.reply("Stopped.")
        elif scheduler.state == 1:
            await context.reply(f"Running. (Staking every {staking_interval} minutes)")
        elif scheduler.state == 2:
            await context.reply("Paused. (How did this even happen? I don't have a pausing function)")

    @cog_ext.cog_slash(name='disableautostaking', guild_ids=slash_guilds)
    @commands.is_owner()
    async def disableautostaking(self, context: SlashContext):
        rtn = scheduler.shutdown()
        if rtn is None:
            await context.reply("Solana auto staking disabled.")
        else:
            await context.reply(rtn)


def setup(client):
    client.add_cog(Staking(client))
