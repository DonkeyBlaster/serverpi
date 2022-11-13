import ftx_functions

positions = []


class Position:
    def __init__(self, ticker: str, size: float, entry: float):
        self.ticker = clean_ticker(ticker)
        self.size = size
        self.entry = entry
        self.cumulative_pnl = 0

    def get_ticker(self) -> str:
        return self.ticker

    def get_size(self) -> float:
        return self.size

    def get_entry(self) -> float:
        return self.entry

    def set_size(self, size: float):
        self.size = round(size, 6)

    def set_entry(self, entry: float):
        self.entry = round(entry, 6)

    def change_pnl(self, pnl: float):
        self.cumulative_pnl += round(pnl, 6)

    def get_pnl(self) -> float:
        return self.cumulative_pnl


def clean_ticker(ticker: str):
    if "-PERP" in ticker:
        return ticker.replace("-PERP", "")
    return ticker


def update_positions():
    positions.clear()
    for pos in ftx_functions.get("positions", {"showAvgPrice": "true"}):
        if pos['netSize'] != 0:
            positions.append(
                Position(
                    ticker=clean_ticker(pos['future']),
                    size=pos['netSize'],
                    entry=abs(pos['recentBreakEvenPrice'])
                ))


def change_position(ticker: str, side: str, size: float, price: float):
    if side == "sell":
        # make size negative if we're selling, this will decrease TN on longs and increase it on shorts
        size *= -1
    # change_position calls are from the ws, these only use positive amounts for the size and sides are always passed
    # however the position objects store things based on positive/negative because that's what ftx passes in the initial get request
    # we will need to get the side of the position and compare to see if we're adding or subtracting
    ticker = clean_ticker(ticker)
    pos: Position
    for pos in positions:
        if pos.get_ticker() == ticker:
            total_notional = abs(pos.get_size() * pos.get_entry() + size * price)
            # get_size returns a pos/neg value based on longs/shorts, this combined with the pos/neg of size will inc/dec positions accordingly
            new_size = pos.get_size() + size
            # if new position size is less than old size and we're positive, we closed (part of) a long
            # also if new position size is more than old size and we're negative, we closed (part of) a short
            if (new_size < pos.get_size() and pos.get_size() > 0) or (new_size > pos.get_size() and pos.get_size() < 0):
                # calculate pnl and tell the position to store it
                diff = price - pos.get_entry()
                # diff will be positive if long profit, negative if short profit
                # positive diff * negative size @ long close means profit is negative, loss is positive
                # negative diff * positive size @ short close means profit is negative, loss positive
                pnl = diff * size * -1  # *-1 since profit is supposed to be positive and vv
                pos.change_pnl(pnl)
            else:
                # we are increasing positions, change our avg entry
                pos.set_entry(abs(total_notional / new_size))

            pos.set_size(new_size)

            return pos

    # no matching position in positions, make a new one
    newpos = Position(
        ticker=ticker,
        size=size,
        entry=price,
    )
    positions.append(newpos)
    return newpos


def check_for_position_clear():
    pos: Position
    for pos in positions:
        if pos.get_size() == 0:
            positions.remove(pos)
            return pos


def get_all_raw_positions() -> list:
    returnable = []
    pos: Position
    for pos in positions:
        returnable.append({"ticker": pos.get_ticker(), "size": pos.get_size(), "entry": pos.get_entry(), "pnl": pos.get_pnl()})
    return returnable
