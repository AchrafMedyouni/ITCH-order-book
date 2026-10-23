from dataclasses import dataclass 
from sortedcontainers import SortedDict
from collections import OrderedDict
@dataclass
class Order: 
    ref: int 
    side: str
    price: int 
    shares: int 
    ts: int

@dataclass 
class Level: 
    price: int 
    orders: OrderedDict[int, Order]  # ref -> Order 
    total : int = 0

class OrderBook: 
    def __init__(self): 
        self.orders = {}
        self.bids = SortedDict() # price -> Level
        self.asks = SortedDict()

    def add(self, order: Order): 
        if order.ref in self.orders: 
            raise KeyError(f"reference {order.ref} already in order book")
        else: 
            self.orders[order.ref] = order
        if order.side == 'B':
            if order.price in self.bids:
                self.bids[order.price].orders[order.ref] = order
            else:
                self.bids[order.price] = Level(order.price, OrderedDict([(order.ref, order)])) # -> order ref, order
            self.bids[order.price].total += order.shares
        elif order.side == 'S':
            if order.price in self.asks:
                self.asks[order.price].orders[order.ref] = order
            else:
                self.asks[order.price] = Level(order.price, OrderedDict([(order.ref, order)]))
            self.asks[order.price].total += order.shares
    def best_bid(self): 
        if len(self.bids) == 0: 
            return None
        else: 
            return (self.bids.peekitem(-1)[0], self.bids.peekitem(-1)[1].total)
    def best_ask(self): 
        if len(self.asks) == 0: 
            return None
        else: 
            return (self.asks.peekitem(0)[0], self.asks.peekitem(0)[1].total)
    def delete(self, ref: int):
        if ref not in self.orders: 
            raise KeyError(f'reference {ref} not in orderbook')
        order = self.orders[ref]
        side = order.side
        shares = order.shares
        price = order.price
        del self.orders[ref]
        if side == 'B':
            level = self.bids[price]
            level.total -= shares 
            if not level.orders:
                del self.bids[price]
            del level.orders[ref]   
        if side == 'S':
            level = self.asks[price]
            level.total -= shares 
            if not level.orders:
                del self.asks[price]
            del level.orders[ref]
    def execute(self, ref: int, shares: int):
        if ref not in self.orders:
            raise KeyError(f'reference {ref} not in orderbook') 
        if shares <= 0:
            raise ValueError(f'shares must be > 0; got {shares}')
        order = self.order[ref] 
        if shares > order.shares: 
            raise ValueError(f'shares superior to shares in the order ({shares} > {order.shares})')
        side = order.side
        side_map = self.bids if side == 'B' else self.asks
        level = side_map[order.price]
        level.total -= shares 
        if not level.orders:
            del side_map[order.price]
        order.shares -= shares 
        if order.shares == 0: 
            self.delete(ref)
        

    def replace(self, ref1: int, ref2: int, price: int, shares: int, ts):
        if ref1 not in self.orders: 
            raise KeyError(f'reference {ref1} not in orderbook')
        if ref2 in self.orders: 
            raise KeyError(f"reference {ref2} already in order book")
        if shares <= 0: 
            raise ValueError('Shares must be positive')
        old_order = self.orders[ref1]
        side = old_order.side
        self.delete(old_order.ref)
        self.add(Order(ref2, side, price, shares, ts))

        
        



