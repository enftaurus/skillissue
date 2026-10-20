#!/usr/bin/env bash
# Skill Issue — Build sandbox language images
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Building Python sandbox image..."
docker build -t skillissue-sandbox-python:latest sandbox/images/python

echo "Building C++ sandbox image..."
docker build -t skillissue-sandbox-cpp:latest sandbox/images/cpp

echo "Building Java sandbox image..."
docker build -t skillissue-sandbox-java:latest sandbox/images/java

echo "All sandbox images built successfully:"
docker images | grep skillissue-sandbox || true
