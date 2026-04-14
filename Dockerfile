FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London

# Install system dependencies
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
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up VNC
ENV DISPLAY=:1
ENV VNC_PORT=5901
ENV NOVNC_PORT=6080
ENV VNC_RESOLUTION=1280x720

RUN mkdir -p /root/.vnc && \
    printf "teamie\nteamie\nn\n" | vncpasswd /root/.vnc/passwd

# VNC xstartup
RUN printf '#!/bin/sh\nunset SESSION_MANAGER\nunset DBUS_SESSION_BUS_ADDRESS\nexec startxfce4\n' > /root/.vnc/xstartup && \
    chmod +x /root/.vnc/xstartup

# Clone the repo and install dependencies
WORKDIR /app
RUN git clone https://github.com/trlmtr/homework-scraper.git . && \
    pip3 install --no-cache-dir -r requirements.txt && \
    playwright install chromium && \
    playwright install-deps

# Create directories for mounted volumes
RUN mkdir -p /app/data/output /app/data/browser_session /app/logs

# Entrypoint
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5901 6080 8088

ENTRYPOINT ["/app/docker-entrypoint.sh"]
