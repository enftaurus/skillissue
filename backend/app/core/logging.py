import logging
import re
import sys

# Regex patterns to sanitize sensitive credentials from any log statement
SENSITIVE_PATTERNS = [
    re.compile(r"(AKIA[0-9A-Z]{16})", re.IGNORECASE),
    re.compile(r"(aws_secret_access_key\s*[:=]\s*['\"]?)([^'\";\s]{10,})(['\"]?)", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9\-_=]+\.[A-Za-z0-9\-_=]+\.?[A-Za-z0-9\-_=]*", re.IGNORECASE),
    re.compile(r"(\"secret_key\"\s*:\s*\")[^\"]+(\")", re.IGNORECASE),
]

class CredentialSanitizingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            msg = record.msg
            for pattern in SENSITIVE_PATTERNS:
                msg = pattern.sub(r"\1[REDACTED]\3" if pattern.groups == 3 else "[REDACTED]", msg)
            record.msg = msg
        return True

def setup_logging():
    logger = logging.getLogger("skillissue")
    logger.setLevel(logging.INFO)
    logger.addFilter(CredentialSanitizingFilter())

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

logger = setup_logging()
