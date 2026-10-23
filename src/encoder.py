"""
Encoder for NASDAQ TotalView-ITCH 5.0 messages: the inverse of messages.decoder.

Guarantees decode(encode(x)) == x for every field stored in the NamedTuples.
Bytes the NamedTuples don't store (tracking number, stock symbol in A/F/P,
unused R fields, ...) are filled with neutral values.
"""
from messages import (
    AddOrder, SystemEvent, StockDirectory, OrderExecuted, StockTradingAction,
    OrderExecutedWithPrice, OrderCancel, OrderDelete, OrderReplace, Trade,
)

STOCK_FILLER = b'TEST    '   # 8-byte symbol for fields the decoder ignores


def _u(n: int, size: int) -> bytes:
    """Unsigned big-endian integer on `size` bytes."""
    return n.to_bytes(size, 'big')


def _alpha(s: str, size: int) -> bytes:
    """ASCII text, left-justified, space-padded to `size` bytes."""
    b = s.encode('ascii')
    if len(b) > size:
        raise ValueError(f"{s!r} longer than {size} bytes")
    return b.ljust(size)


def _header(msg_type: bytes, locate: int, ts: int) -> bytes:
    """11-byte common header: type, locate, tracking number (0), timestamp."""
    return msg_type + _u(locate, 2) + _u(0, 2) + _u(ts, 6)


def _check(out: bytes, expected: int) -> bytes:
    assert len(out) == expected, f"{out[:1]!r}: {len(out)} bytes, expected {expected}"
    return out


# encoding functions (one per message type)
def encode_system_event(m: SystemEvent) -> bytes:
    return _check(_header(b'S', m.locate, m.ts) + _alpha(m.event_code, 1), 12)


def encode_stock_directory(m: StockDirectory) -> bytes:
    out = (_header(b'R', m.locate, m.ts)
           + STOCK_FILLER                    # 11-18 stock
           + _alpha(m.market_category, 1)    # 19
           + b'N'                            # 20 financial status
           + _u(m.round_lot_size, 4)         # 21-24
           + b'N'                            # 25 round lots only
           + _alpha(m.issue_classification, 1)  # 26
           + b'  '                           # 27-28 issue sub-type
           + _alpha(m.authenticity, 1)       # 29
           + b' ' * 4                        # 30-33 SSTI, IPO, LULD tier, ETP flag
           + _u(0, 4)                        # 34-37 ETP leverage factor
           + b'N')                           # 38 inverse indicator
    return _check(out, 39)


def encode_stock_trading_action(m: StockTradingAction) -> bytes:
    out = (_header(b'H', m.locate, m.ts) + STOCK_FILLER
           + _alpha(m.trading_state, 1) + _alpha(m.reserved, 1) + _alpha(m.reason, 4))
    return _check(out, 25)


def encode_add_order(m: AddOrder) -> bytes:
    """Writes an 'A' (36 bytes) if attr is None, otherwise an 'F' (40 bytes)."""
    msg_type = b'A' if m.attr is None else b'F'
    out = (_header(msg_type, m.locate, m.ts) + _u(m.ref, 8) + _alpha(m.side, 1)
           + _u(m.shares, 4) + STOCK_FILLER + _u(m.price, 4))
    if m.attr is None:
        return _check(out, 36)
    return _check(out + _alpha(m.attr, 4), 40)


def encode_order_executed(m: OrderExecuted) -> bytes:
    out = (_header(b'E', m.locate, m.ts) + _u(m.ref, 8) + _u(m.shares, 4)
           + _u(m.match_number, 8))
    return _check(out, 31)


def encode_order_executed_with_price(m: OrderExecutedWithPrice) -> bytes:
    out = (_header(b'C', m.locate, m.ts) + _u(m.ref, 8) + _u(m.shares, 4)
           + _u(m.match_number, 8) + _alpha(m.printable, 1) + _u(m.price, 4))
    return _check(out, 36)


def encode_order_cancel(m: OrderCancel) -> bytes:
    return _check(_header(b'X', m.locate, m.ts) + _u(m.ref, 8) + _u(m.shares, 4), 23)


def encode_order_delete(m: OrderDelete) -> bytes:
    return _check(_header(b'D', m.locate, m.ts) + _u(m.ref, 8), 19)


def encode_order_replace(m: OrderReplace) -> bytes:
    out = (_header(b'U', m.locate, m.ts) + _u(m.ref, 8) + _u(m.new_ref, 8)
           + _u(m.shares, 4) + _u(m.price, 4))
    return _check(out, 35)


def encode_trade(m: Trade) -> bytes:
    out = (_header(b'P', m.locate, m.ts) + _u(0, 8)   # order ref: always 0 in real data
           + _alpha(m.side, 1) + _u(m.shares, 4) + STOCK_FILLER
           + _u(m.price, 4) + _u(m.match_number, 8))
    return _check(out, 44)


ENCODERS = {
    SystemEvent: encode_system_event,
    StockDirectory: encode_stock_directory,
    StockTradingAction: encode_stock_trading_action,
    AddOrder: encode_add_order,
    OrderExecuted: encode_order_executed,
    OrderExecutedWithPrice: encode_order_executed_with_price,
    OrderCancel: encode_order_cancel,
    OrderDelete: encode_order_delete,
    OrderReplace: encode_order_replace,
    Trade: encode_trade,
}


def encode(m) -> bytes:
    """Encodes a message NamedTuple into its ITCH bytes (without length prefix)."""
    try:
        return ENCODERS[type(m)](m)
    except KeyError:
        raise TypeError(f"no encoder for {type(m).__name__}") from None


def frame(m) -> bytes:
    """Encoded message with its 2-byte length prefix, as in the BinaryFILE."""
    body = encode(m)
    return _u(len(body), 2) + body


def write_itch_file(messages, path) -> None:
    """Writes messages to `path` in BinaryFILE format, readable by iter_frames."""
    with open(path, 'wb') as f:
        for m in messages:
            f.write(frame(m))