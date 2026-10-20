import os
import sys

# Assert running as non-root sandbox user
uid = os.getuid()
gid = os.getgid()
if uid != 10001 or gid != 10001:
    print(f"FAIL_UID: uid={uid}, gid={gid}")
    sys.exit(1)

# Assert no sensitive host environment variables leaked
for key in ["SECRET_KEY", "DATABASE_URL", "ENCRYPTION_KEY", "AWS_ACCESS_KEY_ID", "POSTGRES_PASSWORD"]:
    if key in os.environ:
        print(f"FAIL_LEAK_{key}")
        sys.exit(1)

print("ENV_ISOLATED_OK")
