"""Simple HTTP API to trigger the Teamie scraper and serve results.

Endpoints:
  GET /run     - scrape and return results (waits for completion)
  GET /latest  - return latest cached results instantly
  GET /health  - health check
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

OUTPUT_DIR = Path("/app/data/output")
LATEST_FILE = OUTPUT_DIR / "latest.json"


def save_latest(data, auth_failed=False):
    """Save scrape results to latest.json with metadata."""
    output = {
        "last_updated": datetime.now().isoformat(),
        "success": not auth_failed,
        "auth_failed": auth_failed,
        "data": data,
    }
    LATEST_FILE.write_text(json.dumps(output, indent=2))
    return output


def get_latest():
    """Read latest.json if it exists."""
    if LATEST_FILE.exists():
        return json.loads(LATEST_FILE.read_text())
    return None


class ScrapeHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/run":
            self._run_scraper()
        elif self.path == "/latest":
            self._get_latest()
        elif self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "Use /run, /latest, or /health"})

    def _run_scraper(self):
        try:
            result = subprocess.run(
                ["python3", "/app/main.py"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd="/app",
            )

            output_text = result.stdout + result.stderr
            auth_failed = (
                "Authentication failed" in output_text
                or "AUTHENTICATION ERROR" in output_text
                or result.returncode == 1
                and "assignments" not in output_text.lower()
            )

            # Find the latest timestamped output file
            files = sorted(OUTPUT_DIR.glob("teamie_data_*.json"), reverse=True)
            data = None
            if files:
                data = json.loads(files[0].read_text())

            # Save to latest.json
            output = save_latest(data, auth_failed)

            self._respond(200, output)
        except subprocess.TimeoutExpired:
            self._respond(504, {"error": "Scraper timed out after 5 minutes"})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _get_latest(self):
        latest = get_latest()
        if latest:
            self._respond(200, latest)
        else:
            self._respond(404, {"error": "No data yet. Call /run first."})

    def _respond(self, status, data):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode())

    def log_message(self, format, *args):
        print(f"[API] {args[0]}")


if __name__ == "__main__":
    port = 8088
    server = HTTPServer(("0.0.0.0", port), ScrapeHandler)
    print(f"Scraper API listening on port {port}")
    print(f"  GET /run     - scrape and return results")
    print(f"  GET /latest  - return cached results instantly")
    print(f"  GET /health  - health check")
    server.serve_forever()
