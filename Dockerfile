# syntax=docker/dockerfile:1.7

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python, Chrome, and runtime deps
ARG CFT_VERSION=""
ARG CFT_MAJOR="140"

RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      curl gnupg ca-certificates apt-transport-https unzip \
      fonts-liberation libasound2 libnss3 libnspr4 libxss1 libu2f-udev libgbm1 xdg-utils \
      libglib2.0-0 libgtk-3-0 libgdk-pixbuf2.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
      libxkbcommon0 libdbus-1-3 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 \
      libxfixes3 libxi6 libxrandr2 libxrender1 libxtst6 libdrm2 && \
    # Install Chrome for Testing + matching Chromedriver (reliable, version-locked)
    if [ -z "$CFT_VERSION" ]; then \
      if [ -n "$CFT_MAJOR" ]; then \
        CFT_VERSION=$(curl -fsSL https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE_${CFT_MAJOR}); \
      else \
        CFT_VERSION=$(curl -fsSL https://googlechromelabs.github.io/chrome-for-testing/LATEST_RELEASE); \
      fi; \
    fi && \
    curl -fsSL https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chrome-linux64.zip -o /tmp/chrome.zip && \
    curl -fsSL https://storage.googleapis.com/chrome-for-testing-public/${CFT_VERSION}/linux64/chromedriver-linux64.zip -o /tmp/driver.zip && \
    mkdir -p /opt/chrome /opt/chromedriver && \
    unzip -q /tmp/chrome.zip -d /opt && mv /opt/chrome-linux64/* /opt/chrome && \
    unzip -q /tmp/driver.zip -d /opt && mv /opt/chromedriver-linux64/* /opt/chromedriver && \
    chmod +x /opt/chromedriver/chromedriver && ln -sf /opt/chromedriver/chromedriver /usr/local/bin/chromedriver && \
    rm -f /tmp/chrome.zip /tmp/driver.zip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Make Chrome/Driver discoverable
ENV CHROME_BIN=/opt/chrome/chrome
ENV PATH="/opt/chromedriver:${PATH}"

# Install Python deps
COPY requirements.txt ./
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Non-root user
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Default command runs launch_and_store; override args via Machines config.init.cmd
CMD ["python3", "launch_and_store.py"]
