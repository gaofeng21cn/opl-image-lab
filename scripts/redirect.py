"""Optional loopback bookmark for the existing professional ComfyUI UI."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from settings import COMFY_URL, REDIRECT_PORT


class Redirect(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"ui":"ComfyUI","ready":true}')
            return
        self.send_response(302)
        self.send_header("Location", COMFY_URL)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", REDIRECT_PORT), Redirect).serve_forever()
