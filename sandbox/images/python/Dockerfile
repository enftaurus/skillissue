# Pinned minimal Python 3.12 sandbox execution image
FROM python:3.12-slim-bookworm

# Create unprivileged sandbox user
RUN groupadd -g 10001 sandbox && \
    useradd -u 10001 -g sandbox -m -s /bin/sh sandbox && \
    mkdir -p /sandbox && \
    chown -R sandbox:sandbox /sandbox && \
    # Remove package managers and sensitive utilities
    rm -rf /var/lib/apt/lists/* /root/.cache && \
    which pip && rm -f $(which pip) $(which pip3) || true

USER 10001:10001
WORKDIR /sandbox
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD ["python3", "-c", "print('Sandbox Ready')"]
