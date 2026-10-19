from collections import Counter
def iter_frames(filename, limit=None):
    with open(filename, 'rb', buffering=1<<20) as f: 
        i = 0
        while limit is None or i < limit:
            a = f.read(2)
            if not a: return
            if len(a) <  2:
                raise ValueError(f"Error: truncated file at offset {f.tell()}, expected {2} but got {len(a)}.")
            L = int.from_bytes(a, 'big')
            start = f.tell()
            msg = f.read(L)
            if len(msg) < L:
                raise ValueError(f"Error: truncated file at offset {start}, expected {L} but got {len(msg)}.")
            yield msg 
            i += 1
    

def count_messages(filename, limit=None):
    msg_counter = Counter()
    for msg in iter_frames(filename, limit):
        msg_counter[msg[0]] += 1
    return msg_counter

if __name__ == '__main__':
    import sys 
    limit = sys.argv[2] if len(sys.argv) > 2 else 10
    filename = sys.argv[1]
    # Testing the iterframes
    # for i , msg in enumerate(iter_frames(sys.argv[1], int(limit))):
    #     print(i, len(msg), chr(msg[0]), msg[:12].hex(" "))
    count = count_messages(filename, int(limit))
    print({chr(e): count[e] for e in count})
        