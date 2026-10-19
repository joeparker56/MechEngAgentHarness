# mecheng-fea: base stack + CalculiX.
# Build from the repo root:  docker build -f docker/fea/Dockerfile -t mecheng-fea:dev .
ARG BASE_IMAGE=mecheng-base:dev
FROM ${BASE_IMAGE}

RUN apt-get update && apt-get install -y --no-install-recommends calculix-ccx \
    && rm -rf /var/lib/apt/lists/*
