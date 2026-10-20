import os
import sys

# Attempt reading sensitive host paths or canary
canary_paths = [
    "/tmp/skillissue_canary.txt",
    "/etc/shadow",
    "/root/.ssh/id_rsa",
    "../backend/.env",
    "../../.env",
]

for path in canary_paths:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                content = f.read()
                if content:
                    print(f"CANARY_BREACH:{path}")
                    sys.exit(1)
        except Exception:
            pass

print("FILESYSTEM_ISOLATED_OK")
