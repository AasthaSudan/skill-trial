#!/usr/bin/env bash
set -euo pipefail

command -v docker >/dev/null || { echo "Docker CLI is required." >&2; exit 2; }
docker info --format '{{.ServerVersion}}' >/dev/null
runtime="${OCI_RUNTIME:-runsc}"
if [[ "$runtime" == "runsc" ]]; then
  docker info --format '{{json .Runtimes}}' | grep -q '"runsc"' || {
    echo "The Docker daemon does not expose the runsc runtime. Install and configure gVisor first." >&2
    exit 2
  }
elif [[ "$runtime" != "runc" ]]; then
  echo "OCI_RUNTIME must be runsc or runc." >&2
  exit 2
fi

for image in python:3.12-alpine node:22-alpine eclipse-temurin:21-jdk-alpine; do
  docker pull "$image"
done
echo "Runner runtime and language images are prepared."
