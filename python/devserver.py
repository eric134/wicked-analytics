"""
Local preview server with caching turned off, so edits to js/css show up on a
plain reload. Only for development — GitHub Pages handles caching in production.
"""

import http.server
import os
import socketserver

PORT = 8080
os.chdir(os.path.join(os.path.dirname(__file__), ".."))


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, must-revalidate")
        self.send_header("Expires", "0")
        super().end_headers()


with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    print(f"Serving http://localhost:{PORT} (no-cache)")
    httpd.serve_forever()
