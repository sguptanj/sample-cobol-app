
FROM ubuntu:26.04

LABEL maintainer="BuildPiper"
LABEL description="Ubuntu 26.04 base image with GnuCOBOL CI/CD dependencies"

ENV DEBIAN_FRONTEND=noninteractive

# Install build and runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gnucobol \
    build-essential \
    gcc \
    make \
    python3 \
    python3-pip \
    git \
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

# Verify installed dependencies
RUN cobc --version && \
    gcc --version && \
    make --version && \
    python3 --version && \
    git --version

WORKDIR /workspace

CMD ["/bin/bash"]

