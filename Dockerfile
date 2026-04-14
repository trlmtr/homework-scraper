FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London

# Install system dependencies (use Firefox instead of Chromium snap stub)
RUN apt-get update && apt-get install -y \
    tightvncserver \
    xfce4 \
    xfce4-terminal \
    novnc \
    websockify \
    python3 \
    python3-pip \
    firefox \
    dbus-x11 \
    xdg-utils \
    fonts-liberation \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up VNC password using tightvnc's expect-style input
ENV DISPLAY=:1
ENV VNC_PORT=5901
ENV NOVNC_PORT=6080
ENV VNC_RESOLUTION=1280x720

RUN mkdir -p /root/.vnc && \
    printf "teamie\nteamie\nn\n" | vncpasswd /root/.vnc/passwd

# VNC xstartup
RUN printf '#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4\n' > /root/.vnc/xstartup && \
    chmod +x /root/.vnc/xstartup

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps

# Copy scraper code
COPY config/ ./config/
COPY teamie_scraper/ ./teamie_scraper/
COPY main.py scrape_combined.py api.py ./

# Create directories for mounted volumes
RUN mkdir -p /app/data/output /app/data/browser_session /app/logs

# Startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

EXPOSE 5901 6080 8088

ENTRYPOINT ["/docker-entrypoint.sh"]
