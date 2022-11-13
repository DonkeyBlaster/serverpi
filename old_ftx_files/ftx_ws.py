import json
import time
import discord
import websockets
import hmac
import ftx_functions
import ftx_positionmanager


def _get_auth_json():
    ts = int(time.time() * 1000)
    sign = hmac.new(ftx_functions.api_secret.encode(), f'{ts}websocket_login'.encode(), 'sha256').hexdigest()
    return f'{{"op": "login", "args": {{"key": "{ftx_functions.api_key}", "sign": "{sign}", "time": {ts}}}}}'


async def main_loop(client):
    async for websocket in websockets.connect("wss://ftx.com/ws"):
        try:
            # get positions just before doing anything with ws, we can update positions with fill events later
            ftx_positionmanager.update_positions()

            await websocket.send(_get_auth_json())
            await websocket.send('{"op": "subscribe", "channel": "fills"}')
            while True:
                data = json.loads(await websocket.recv())
                if data['type'] == "update" and data['channel'] == "fills":
                    if client.notify_next_fill:
                        await client.futures_channel.send("<@291661685863874560>")
                        client.notify_next_fill = False

                    ticker = data['data']['future']
                    side = data['data']['side']
                    amt = data['data']['size']
                    price = data['data']['price']

                    color = 0x00ff00 if side == "buy" else 0xff0000

                    position: ftx_positionmanager.Position = ftx_positionmanager.change_position(ticker, side, amt, price)

                    await client.futures_channel.send(embed=discord.Embed(title="Order filled", color=color, description=f"{side.capitalize()} {amt} {ticker} @ ${price}").set_footer(text=f"Total: {position.get_size()} @ ${position.get_entry()}"))

                    cpos = ftx_positionmanager.check_for_position_clear()
                    if cpos:
                        # position cleared means we closed a position, get the cumulative pnl from the closed position
                        color = 0x00ff00 if cpos.cumulative_pnl > 0 else 0xff0000
                        await client.futures_channel.send(embed=discord.Embed(title=f"{ticker} Position closed", color=color, description=f"PnL: ${round(cpos.cumulative_pnl, 4)}"))

                elif data['type'] == "info" and data['code'] == 20001:
                    await client.futures_channel.send("code 20001, reconnecting")
                    raise websockets.ConnectionClosed
                elif data['type'] == "subscribed" or data['type'] == "unsubscribed":
                    pass
                    # await client.futures_channel.send(data)
                else:
                    await client.futures_channel.send(f"could not parse `{data}`")
        except Exception as e:
            if not isinstance(e, websockets.ConnectionClosedError):
                print(f"error: {e}")
                continue
