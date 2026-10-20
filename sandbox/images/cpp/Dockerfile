# Lightweight minimal GCC 13/14 C++ sandbox execution image
FROM alpine:3.20

RUN apk add --no-cache g++ libstdc++ musl-dev && \
    addgroup -g 10001 -S sandbox && \
    adduser -u 10001 -S sandbox -G sandbox && \
    mkdir -p /sandbox && \
    chown -R sandbox:sandbox /sandbox && \
    rm -rf /var/cache/apk/*

USER 10001:10001
WORKDIR /sandbox

CMD ["g++", "--version"]
