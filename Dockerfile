# syntax=docker/dockerfile:1.7

FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install Python, Chrome, and runtime deps
RUN apt-get update && apt-get install -y --no-install-recommends \
      python3 python3-pip python3-venv \
      curl gnupg ca-certificates apt-transport-https unzip \
      fonts-liberation libasound2 libnss3 libnspr4 libxss1 libu2f-udev libgbm1 xdg-utils \
      libglib2.0-0 libgtk-3-0 libgdk-pixbuf2.0-0 libatk-bridge2.0-0 libatspi2.0-0 \
      libxkbcommon0 libdbus-1-3 libcairo2 libpango-1.0-0 libpangocairo-1.0-0 \
      libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 \
      libxfixes3 libxi6 libxrandr2 libxrender1 libxtst6 libdrm2 && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-linux.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-linux.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y --no-install-recommends google-chrome-stable && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

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


