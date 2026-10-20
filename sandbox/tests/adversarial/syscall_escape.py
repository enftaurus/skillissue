import ctypes
import sys

# Attempt blocked syscalls: ptrace, unshare
try:
    libc = ctypes.CDLL(None)
    # ptrace(PTRACE_TRACEME, 0, 1, 0)
    res = libc.ptrace(0, 0, 1, 0)
    if res == 0:
        print(f"PTRACE_SUCCEEDED:{res}")
        sys.exit(1)
except Exception:
    pass

print("SECCOMP_ISOLATED_OK")
