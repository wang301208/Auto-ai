# 'dev' or 'release' container build
ARG BUILD_TYPE=dev

# Use an official Python base image from the Docker Hub
FROM python:3.10-slim AS autogpt-base

# Install browsers
RUN apt-get update && apt-get install -y \
    chromium-driver firefox-esr ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install utilities
RUN apt-get update && apt-get install -y \
    curl jq wget git \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PIP_NO_CACHE_DIR=yes \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install the required python packages globally
ENV PATH="$PATH:/root/.local/bin"

# Set the entrypoint
ENTRYPOINT ["python", "-m", "autogpt", "--install-plugin-deps"]

# dev build -> include everything
FROM autogpt-base as autogpt-dev
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -e .[dev,test,alphaevolve]

# release build -> include bare minimum
FROM autogpt-base as autogpt-release
WORKDIR /app
COPY pyproject.toml README.md ./
COPY autogpt/ ./autogpt
COPY scripts/ ./scripts
COPY plugins/ ./plugins
COPY prompt_settings.yaml ./prompt_settings.yaml
RUN pip install --no-cache-dir .
RUN mkdir ./data

FROM autogpt-${BUILD_TYPE} AS auto-gpt
