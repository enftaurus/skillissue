# Pinned minimal OpenJDK 21 sandbox execution image
FROM eclipse-temurin:21-jdk-jammy

RUN groupadd -g 10001 sandbox && \
    useradd -u 10001 -g sandbox -m -s /bin/sh sandbox && \
    mkdir -p /sandbox && \
    chown -R sandbox:sandbox /sandbox && \
    rm -rf /var/lib/apt/lists/* /root/.cache

USER 10001:10001
WORKDIR /sandbox

CMD ["java", "-version"]
