import pytest

from messages import (
    decoder, AddOrder, SystemEvent, StockDirectory, OrderExecuted, StockTradingAction,
    OrderExecutedWithPrice, OrderCancel, OrderDelete, OrderReplace, Trade,
)
from encoder import encode, write_itch_file
from reader import iter_frames

TS = 34_200_000_000_000      # 09:30:00.000000000
AAPL = 24

SAMPLES = [
    SystemEvent(TS, 0, 'O'),
    StockDirectory(TS, AAPL, 'Q', 100, 'P', 'C'),
    StockTradingAction(TS, AAPL, 'T', ' ', ''),
    AddOrder(TS, AAPL, 20073, 'B', 100, 2779100),
    AddOrder(TS, AAPL, 20074, 'S', 300, 2786400, 'ABCD'),        # -> 'F'
    OrderExecuted(TS, AAPL, 20089, 2, 24236),
    OrderExecutedWithPrice(TS, AAPL, 20089, 50, 24237, 2780000, 'Y'),
    OrderCancel(TS, AAPL, 953509, 200),
    OrderDelete(TS, AAPL, 20073),
    OrderReplace(TS, AAPL, 42777, 45045, 100, 2779600),
    Trade(TS, AAPL, 12, 2785900, 24441),
]


@pytest.mark.parametrize("msg", SAMPLES, ids=lambda m: type(m).__name__)
def test_round_trip(msg):
    decoded = decoder(encode(msg))
    assert type(decoded) is type(msg)
    assert decoded == msg


@pytest.mark.parametrize("msg", [
    AddOrder(2**48 - 1, 2**16 - 1, 2**64 - 1, 'S', 2**32 - 1, 2_000_000_000),
    OrderReplace(2**48 - 1, 2**16 - 1, 2**64 - 1, 2**64 - 1, 2**32 - 1, 2_000_000_000),
], ids=["AddOrder-max", "OrderReplace-max"])
def test_round_trip_max_values(msg):
    assert decoder(encode(msg)) == msg


def test_add_order_type_byte():
    assert encode(SAMPLES[3])[:1] == b'A' and len(encode(SAMPLES[3])) == 36
    assert encode(SAMPLES[4])[:1] == b'F' and len(encode(SAMPLES[4])) == 40


def test_golden_system_event():
    """First message of S120825-v50, decoded by hand."""
    raw = bytes.fromhex("53 0000 0000 09e74db02102 4f".replace(" ", ""))
    assert decoder(raw) == SystemEvent(10_889_045_483_778, 0, 'O')


def test_file_round_trip(tmp_path):
    path = tmp_path / "mini.itch"
    write_itch_file(SAMPLES, path)
    assert [decoder(m) for m in iter_frames(path)] == SAMPLES
