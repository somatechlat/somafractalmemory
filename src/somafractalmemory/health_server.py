"""
Minimal health server for fallback mode (no API server)
Serves /health, /livez, /readyz on configured port
"""

import http.server
import json
import os
import socketserver

PORT = int(os.environ.get("SFM_API_PORT", "9595"))
HOST = os.environ.get("SFM_API_HOST", "0.0.0.0")


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health", "/livez", "/readyz"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {"status": "ok", "port": PORT, "docs": "set SFM_SERVER=1 to enable /docs"}
                ).encode("utf-8")
            )
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()
