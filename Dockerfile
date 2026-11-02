
FROM ubuntu:26.04

LABEL maintainer="BuildPiper"
LABEL description="Ubuntu 26.04 COBOL CI/CD execution environment"

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    gnucobol \
    build-essential \
    gcc \
    make \
    python3 \
    python3-pip \
    git \
    docker.io \
    bash \
    curl \
    wget \
    ca-certificates \
    tar \
    gzip \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    file \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN cobc --version && \
    gcc --version && \
    make --version && \
    python3 --version && \
    git --version && \
    docker --version

WORKDIR /workspace

CMD ["/bin/bash"]

