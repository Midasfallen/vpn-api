#!/usr/bin/env python3
"""Simple reverse proxy: listens on 0.0.0.0:5000 and forwards to http://127.0.0.1:8000.

Uses standard library only so no extra dependencies are required on the host.
"""
import http.client
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

TARGET_HOST = "127.0.0.1"
TARGET_PORT = 8000


class ProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _proxy_request(self):
        length = (
            int(self.headers.get("Content-Length", 0)) if "Content-Length" in self.headers else 0
        )
        body = self.rfile.read(length) if length else None
        path = self.path
        conn = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=10)
        hop_by_hop = [
            "Connection",
            "Keep-Alive",
            "Proxy-Authenticate",
            "Proxy-Authorization",
            "TE",
            "Trailers",
            "Transfer-Encoding",
            "Upgrade",
        ]
        headers = {k: v for k, v in self.headers.items() if k not in hop_by_hop}
        headers["Host"] = f"{TARGET_HOST}:{TARGET_PORT}"
        try:
            conn.request(self.command, path, body=body, headers=headers)
            resp = conn.getresponse()
            resp_body = resp.read()
            self.send_response(resp.status, resp.reason)
            for key, val in resp.getheaders():
                if key.lower() == "transfer-encoding" and "chunked" in val.lower():
                    continue
                if key.lower() == "connection":
                    continue
                self.send_header(key, val)
            self.send_header("Content-Length", str(len(resp_body)))
            self.end_headers()
            if resp_body:
                self.wfile.write(resp_body)
        except Exception as e:
            self.send_response(502)
            self.send_header("Content-Type", "text/plain")
            msg = f"Proxy error: {e}\n"
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg.encode("utf-8"))
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def do_GET(self):
        self._proxy_request()

    def do_POST(self):
        self._proxy_request()

    def do_PUT(self):
        self._proxy_request()

    def do_DELETE(self):
        self._proxy_request()

    def do_PATCH(self):
        self._proxy_request()

    def do_HEAD(self):
        self._proxy_request()


if __name__ == "__main__":
    port = 5000
    server = HTTPServer(("0.0.0.0", port), ProxyHandler)
    print(f"Proxying 0.0.0.0:{port} -> {TARGET_HOST}:{TARGET_PORT}", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
