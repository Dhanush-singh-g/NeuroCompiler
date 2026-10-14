"""Serve only dashboard assets; Python standard library, no compiler required."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1] / 'dashboard'
ASSETS = {'index.html', 'style.css', 'app.js', 'results.js', 'data.json',
          'reports/EXPANDED_SL.md', 'reports/PERSISTENT_SL.md', 'reports/FINAL_ASSESSMENT.md'}


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        requested = 'index.html' if path == '/' else path.lstrip('/')
        if requested not in ASSETS:
            self.send_error(404)
            return
        asset = Path(self.directory) / requested
        if asset.is_symlink() or not asset.resolve().is_relative_to(Path(self.directory).resolve()):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        # Apply the same allowlist to HEAD requests, without sending a body.
        self._head = True
        try:
            self.do_GET()
        finally:
            self._head = False

    def copyfile(self, source, outputfile):
        if not getattr(self, '_head', False):
            super().copyfile(source, outputfile)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        super().end_headers()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    if not (ROOT / 'results.js').is_file():
        parser.error('First run: python scripts/build_dashboard.py')
    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(ROOT)))
    print(f'Dashboard listening on {args.host}:{server.server_port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
