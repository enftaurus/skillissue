import socket
import sys

# Attempt outbound connections: public internet, AWS metadata, and local ports
targets = [
    ("8.8.8.8", 53),
    ("169.254.169.254", 80),
    ("127.0.0.1", 5433),
    ("127.0.0.1", 8001),
]

for host, port in targets:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.5)
    try:
        s.connect((host, port))
        print(f"NETWORK_BREACH:{host}:{port}")
        s.close()
        sys.exit(1)
    except Exception:
        pass
    finally:
        s.close()

print("NETWORK_ISOLATED_OK")
