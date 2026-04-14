"""Simple HTTP API to trigger the Teamie scraper and serve results."""

import asyncio
import json
import subprocess
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread


OUTPUT_DIR = Path("/app/data/output")


class ScrapeHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        if self.path == "/run":
            self._run_scraper()
        elif self.path == "/latest":
            self._get_latest()
        elif self.path == "/health":
            self._respond(200, {"status": "ok"})
        else:
            self._respond(404, {"error": "Not found. Use /run, /latest, or /health"})

    def _run_scraper(self):
        try:
            result = subprocess.run(
                ["python3", "/app/main.py"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd="/app",
            )

            # Find the latest output file
            latest = self._find_latest_output()
            data = None
            if latest:
                data = json.loads(latest.read_text())

            self._respond(200, {
                "success": result.returncode == 0,
                "stdout": result.stdout[-2000:] if result.stdout else "",
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "data": data,
            })
        except subprocess.TimeoutExpired:
            self._respond(504, {"error": "Scraper timed out after 5 minutes"})
        except Exception as e:
            self._respond(500, {"error": str(e)})

    def _get_latest(self):
        latest = self._find_latest_output()
        if latest:
            data = json.loads(latest.read_text())
            self._respond(200, data)
        else:
            self._respond(404, {"error": "No output files found"})

    def _find_latest_output(self):
        files = sorted(OUTPUT_DIR.glob("teamie_data_*.json"), reverse=True)
        return files[0] if files else None

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
    print(f"  GET /run     - trigger scraper")
    print(f"  GET /latest  - get latest results")
    print(f"  GET /health  - health check")
    server.serve_forever()
