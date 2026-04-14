#!/bin/bash
set -e

export USER=root

# Start VNC server (tightvnc)
vncserver :1 -geometry ${VNC_RESOLUTION:-1920x1080} -depth 24

# Start noVNC (web-based VNC client)
websockify --web /usr/share/novnc ${NOVNC_PORT:-6080} localhost:${VNC_PORT:-5901} &

# Start scraper API
python3 /app/api.py &

echo "============================================"
echo "  Teamie Scraper Container Ready"
echo "============================================"
echo "  noVNC:  http://localhost:${NOVNC_PORT:-6080}/vnc.html"
echo "  VNC:    localhost:${VNC_PORT:-5901}"
echo "  API:    http://localhost:8088"
echo "============================================"
echo ""
echo "  API endpoints:"
echo "    GET /run     - trigger scraper"
echo "    GET /latest  - get latest results"
echo "    GET /health  - health check"
echo "============================================"

# Keep container running
tail -f /dev/null
