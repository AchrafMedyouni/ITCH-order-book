
from typing import NamedTuple

"""
Message Types definitions for the NASDAQ TotalView-ITCH 5.0 protocol.
"""
# A
class AddOrder(NamedTuple): 
    ts: int
    locate: int 
    ref: int 
    side: str
    shares: int 
    price: int 
    attr: str | None = None 
# S
class SystemEvent(NamedTuple): 
     ts: int 
     locate: int
     event_code: str 
# R
class StockDirectory(NamedTuple): 
    ts: int 
    locate: int 
    market_category: str 
    round_lot_size: int
    authenticity: str 
    issue_classification: str 
# E 
class OrderExecuted(NamedTuple): 
    ts: int 
    locate: int 
    ref: int 
    shares: int
    match_number: int
# H 
class StockTradingAction(NamedTuple): 
    ts: int 
    locate: int 
    trading_state: str 
    reserved: str 
    reason: str
# C
class OrderExecutedWithPrice(NamedTuple): 
    ts: int 
    locate: int 
    ref: int 
    shares: int 
    match_number: int 
    price: int 
    printable: str 
# X 
class OrderCancel(NamedTuple): 
    ts: int 
    locate: int 
    ref: int 
    shares: int
# D 
class OrderDelete(NamedTuple): 
    ts: int 
    locate: int 
    ref: int 
# U
class OrderReplace(NamedTuple): 
    ts: int 
    locate: int 
    ref: int 
    new_ref: int 
    shares: int 
    price: int 

# P 
class Trade(NamedTuple): 
    ts: int 
    locate: int 
    shares: int 
    price: int 
    match_number: int
    side : str = "B"


def decode_header_helper(msg) -> tuple: 
    """
        Returns a tuple in the form (stock locate, timestamp)
    """
    return (int.from_bytes(msg[1:3], 'big'), int.from_bytes(msg[5:11], 'big'))
# decoding functions 
def decode_system_event(msg): 
    locate, ts= decode_header_helper(msg)
    return SystemEvent(ts, locate, chr(msg[11]))

def decode_add_order(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    side  = chr(msg[19])
    shares = int.from_bytes(msg[20:24], 'big')
    price = int.from_bytes(msg[32:36], 'big')
    return AddOrder(ts, locate, ref, side, shares, price)

def decode_trade(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    shares = int.from_bytes(msg[20:24], 'big')
    price = int.from_bytes(msg[32:36], 'big')
    match_number = int.from_bytes(msg[36:44], 'big')
    return Trade(ts, locate, shares, price, match_number)
def decode_order_executed(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    shares = int.from_bytes(msg[19:23], 'big')
    match_number = int.from_bytes(msg[23:31], 'big')
    return OrderExecuted(ts, locate, ref, shares, match_number)
def decode_order_executed_with_price(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    shares = int.from_bytes(msg[19:23], 'big')
    match_number = int.from_bytes(msg[23:31], 'big')
    printable = chr(msg[31])
    price = int.from_bytes(msg[32:36], 'big')

    return OrderExecutedWithPrice(ts, locate, ref, shares, match_number, price, printable)
def decode_order_cancel(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    shares = int.from_bytes(msg[19:], 'big')
    return OrderCancel(ts, locate, ref, shares)

def decode_order_replace(msg): 
    locate,ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    new_ref = int.from_bytes(msg[19:27], 'big')
    shares = int.from_bytes(msg[27:31], 'big')
    price = int.from_bytes(msg[31:], 'big')
    return OrderReplace(ts, locate, ref,new_ref, shares, price)
def decode_stock_trading_action(msg): 
    locate, ts = decode_header_helper(msg)
    trading_state = chr(msg[19])
    reserved = chr(msg[20])
    reason = msg[21:25].decode('ascii').rstrip()
    return StockTradingAction(ts, locate, trading_state, reserved, reason)
def decode_order_delete(msg): 
    locate, ts = decode_header_helper(msg)
    ref = int.from_bytes(msg[11:19], 'big')
    return OrderDelete(ts,locate,ref)
def decode_stock_directory(msg):
    locate, ts = decode_header_helper(msg)
    market_category = chr(msg[19])
    round_lot_size = int.from_bytes(msg[21:25], 'big')
    authenticity = chr(msg[29])
    issue_classification = chr(msg[26])
    return StockDirectory(ts, locate, market_category, round_lot_size, authenticity, issue_classification)

TYPE_MAP = {
    b'A': decode_add_order,
    b'S': decode_system_event,
    b'R': decode_stock_directory,
    b'E': decode_order_executed,
    b'H': decode_stock_trading_action,
    b'C': decode_order_executed_with_price,
    b'X': decode_order_cancel,
    b'D': decode_order_delete,
    b'U': decode_order_replace,
    b'P': decode_trade
}
def decoder(msg: bytes) -> NamedTuple: 
    """ Decodes a message and returns a representation as  a NamedTuple. """
    if msg[0:1] in TYPE_MAP: 
        return TYPE_MAP[msg[0:1]](msg)
    else: return None

if __name__ == '__main__':
    import sys
    from collections import Counter
    from reader import iter_frames

    PATH = sys.argv[1] if len(sys.argv) > 1 else "data/S120825-v50.txt"
    LOCATE = 24                       # AAPL on 2025-12-08 only
    WANTED = [b'A', b'F', b'E', b'C', b'X', b'D', b'U', b'P']
    PER_TYPE = 3
    LIMIT = 20_000_000                # safety net

    def fmt_ts(ns):
        s, ns = divmod(ns, 1_000_000_000)
        h, s = divmod(s, 3600)
        m, s = divmod(s, 60)
        return f"{h:02}:{m:02}:{s:02}.{ns:09}"

    seen = Counter()
    scanned = 0
    for msg in iter_frames(PATH, LIMIT):
        scanned += 1
        t = msg[0:1]
        if t not in WANTED or seen[t] >= PER_TYPE:
            continue
        if int.from_bytes(msg[1:3], 'big') != LOCATE:   # cheap filter before decoding
            continue
        m = decoder(msg)
        seen[t] += 1
        price = getattr(m, 'price', None)
        extra = f"  ${price / 10_000:.4f}" if price is not None else ""
        print(f"{t.decode()}  {fmt_ts(m.ts)}{extra}\n   {m}")
        if all(seen[w] >= PER_TYPE for w in WANTED):
            break

    print(f"\nscanned {scanned:,} messages")
    for w in WANTED:
        flag = "" if seen[w] >= PER_TYPE else "   <- not enough found"
        print(f"  {w.decode()}: {seen[w]}{flag}")


