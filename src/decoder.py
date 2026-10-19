def build_symbol_map(iterator): 
    symbols = {}
    for msg in iterator: 
        if msg[0] == 0x52:
            locate = int.from_bytes(msg[1:3], 'big')
            symbols[locate] = msg[11:19].decode('ascii').rstrip()
        elif msg[0] == 0x41:
            break
    return symbols

if __name__ == '__main__':
    from reader import iter_frames as iterator
    symbols = build_symbol_map(iterator('data/S120825-v50.txt'))
    print([(e,symbols[e]) for e in symbols if symbols[e] == 'AAPL'])
