"""Tests for src/book.py — OrderBook (add / best_bid / best_ask / delete / execute / replace)."""
import copy

import pytest

from book import Order, OrderBook

# Prices are raw ITCH ints (4 implied decimals): 2781000 = $278.10
P_HI = 2781000   # 278.10
P_LO = 2780500   # 278.05
A_LO = 2781200   # 278.12
A_HI = 2781500   # 278.15


# ---------- helpers ----------

def o(ref, side, price, shares, ts=0):
    return Order(ref, side, price, shares, ts)


def queue(book, side, price):
    """Refs at a price level, in FIFO order."""
    side_map = book.bids if side == "B" else book.asks
    return list(side_map[price].orders.keys())


def snapshot(book):
    """Plain-data copy of the book, to check that a failed call changed nothing."""
    def side(m):
        return {p: (lvl.total, [(r, x.shares) for r, x in lvl.orders.items()]) for p, lvl in m.items()}
    return (
        {r: (x.side, x.price, x.shares, x.ts) for r, x in book.orders.items()},
        side(book.bids),
        side(book.asks),
    )


def check_invariants(book):
    """Consistency rules that must hold after every operation."""
    seen = set()
    for side, side_map in (("B", book.bids), ("S", book.asks)):
        for price, lvl in side_map.items():
            assert lvl.orders, f"empty level left at {price}"
            assert lvl.total == sum(x.shares for x in lvl.orders.values()), f"bad total at {price}"
            for ref, x in lvl.orders.items():
                assert x.shares > 0, f"order {ref} has {x.shares} shares"
                assert x.side == side and x.price == price, f"order {ref} in wrong level"
                assert book.orders.get(ref) is x, f"order {ref} in level but not in book.orders"
                seen.add(ref)
    assert seen == set(book.orders), "book.orders and levels disagree"


@pytest.fixture
def book():
    """#1 B 100 @ 278.10, #2 B 50 @ 278.10, #3 B 200 @ 278.05,
       #10 S 80 @ 278.12, #11 S 300 @ 278.15"""
    b = OrderBook()
    b.add(o(1, "B", P_HI, 100, ts=1))
    b.add(o(2, "B", P_HI, 50, ts=2))
    b.add(o(3, "B", P_LO, 200, ts=3))
    b.add(o(10, "S", A_LO, 80, ts=4))
    b.add(o(11, "S", A_HI, 300, ts=5))
    return b


# ---------- add / BBO ----------

def test_empty_book():
    b = OrderBook()
    assert b.best_bid() is None
    assert b.best_ask() is None


def test_three_bids_two_prices():
    b = OrderBook()
    b.add(o(1, "B", P_HI, 100))
    b.add(o(2, "B", P_HI, 50))
    b.add(o(3, "B", P_LO, 200))
    assert b.best_bid() == (P_HI, 150)
    assert b.best_ask() is None
    assert queue(b, "B", P_HI) == [1, 2]
    check_invariants(b)


def test_best_ask_is_lowest(book):
    assert book.best_ask() == (A_LO, 80)
    assert book.best_bid() == (P_HI, 150)
    check_invariants(book)


def test_add_duplicate_ref_raises(book):
    before = snapshot(book)
    with pytest.raises(KeyError):
        book.add(o(1, "S", A_HI, 10))
    assert snapshot(book) == before


def test_add_bad_side_raises_and_leaves_book_unchanged():
    b = OrderBook()
    with pytest.raises(ValueError):
        b.add(o(1, "X", P_HI, 100))
    assert 1 not in b.orders
    check_invariants(b)


# ---------- delete ----------

def test_delete_one_of_two_keeps_level(book):
    book.delete(1)
    assert book.best_bid() == (P_HI, 50)
    assert queue(book, "B", P_HI) == [2]
    assert 1 not in book.orders
    check_invariants(book)


def test_delete_only_order_removes_level(book):
    book.delete(10)
    assert A_LO not in book.asks
    assert book.best_ask() == (A_HI, 300)
    check_invariants(book)


def test_delete_whole_best_level_moves_bbo(book):
    book.delete(1)
    book.delete(2)
    assert P_HI not in book.bids
    assert book.best_bid() == (P_LO, 200)
    check_invariants(book)


def test_delete_last_order_empties_side():
    b = OrderBook()
    b.add(o(1, "S", A_LO, 10))
    b.delete(1)
    assert b.best_ask() is None
    assert len(b.asks) == 0
    check_invariants(b)


def test_delete_unknown_ref_raises(book):
    before = snapshot(book)
    with pytest.raises(KeyError):
        book.delete(999)
    assert snapshot(book) == before


# ---------- execute ----------

def test_partial_execute_keeps_queue_position(book):
    book.execute(1, 30)
    assert book.orders[1].shares == 70
    assert book.best_bid() == (P_HI, 120)
    assert queue(book, "B", P_HI) == [1, 2]   # #1 still first
    check_invariants(book)


def test_full_execute_removes_order_everywhere(book):
    book.execute(1, 100)
    assert 1 not in book.orders
    assert queue(book, "B", P_HI) == [2]      # gone from the level too
    assert book.best_bid() == (P_HI, 50)
    check_invariants(book)


def test_full_execute_only_order_removes_level(book):
    book.execute(10, 80)
    assert A_LO not in book.asks
    assert book.best_ask() == (A_HI, 300)
    check_invariants(book)


def test_execute_in_steps_to_zero(book):
    book.execute(3, 50)
    book.execute(3, 150)
    assert 3 not in book.orders
    assert P_LO not in book.bids
    check_invariants(book)


@pytest.mark.parametrize("ref, shares, exc", [
    (999, 10, KeyError),     # unknown ref
    (1, 101, ValueError),    # more than the order has
    (1, 0, ValueError),      # zero
    (1, -5, ValueError),     # negative
])
def test_execute_invalid_raises_and_leaves_book_unchanged(book, ref, shares, exc):
    before = snapshot(book)
    with pytest.raises(exc):
        book.execute(ref, shares)
    assert snapshot(book) == before


# ---------- replace ----------

def test_replace_same_price_loses_queue_position(book):
    book.replace(1, 4, P_HI, 100, ts=99)
    assert queue(book, "B", P_HI) == [2, 4]   # #4 behind #2
    assert 1 not in book.orders
    assert book.orders[4].ts == 99            # U message's timestamp, not the old one
    assert book.best_bid() == (P_HI, 150)
    check_invariants(book)


def test_replace_inherits_side(book):
    book.replace(10, 12, A_LO, 40, ts=99)
    assert book.orders[12].side == "S"
    assert book.best_ask() == (A_LO, 40)
    check_invariants(book)


def test_replace_new_price_moves_order_and_drops_empty_level(book):
    book.replace(3, 4, P_HI, 200, ts=99)
    assert P_LO not in book.bids
    assert queue(book, "B", P_HI) == [1, 2, 4]
    assert book.best_bid() == (P_HI, 350)
    check_invariants(book)


@pytest.mark.parametrize("old, new, shares, exc", [
    (999, 4, 10, KeyError),   # unknown old ref
    (1, 2, 10, KeyError),     # new ref already live
    (1, 4, 0, ValueError),    # zero shares
])
def test_replace_invalid_raises_and_leaves_book_unchanged(book, old, new, shares, exc):
    before = snapshot(book)
    with pytest.raises(exc):
        book.replace(old, new, P_HI, shares, ts=99)
    assert snapshot(book) == before