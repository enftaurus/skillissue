# Attempt allocating 1GB of memory to trigger OOM / memory limit
try:
    data = []
    while True:
        data.append(b"A" * (50 * 1024 * 1024))
except MemoryError:
    print("MEMORY_CAUGHT")
