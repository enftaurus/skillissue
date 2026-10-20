import os
import sys

# Fork bomb attempt to exhaust PIDs
try:
    while True:
        os.fork()
except Exception as e:
    # Will fail once pids_limit (64) is reached
    print(f"FORK_BLOCKED:{e}")
