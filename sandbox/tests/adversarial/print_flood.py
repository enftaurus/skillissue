import sys

# Attempt flood of unbounded output to overwhelm host memory
chunk = "X" * 100000 + "\n"
for _ in range(500):
    sys.stdout.write(chunk)
    sys.stdout.flush()
