"""로컬 HTTP 서버: GET / 및 /api/* — Lambda와 동일 핸들러 호출."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import urlparse

from handler import lambda_handler


class _H(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path or "/"
        qs = {}
        if parsed.query:
            for part in parsed.query.split("&"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    qs[k] = v
        event: dict[str, Any] = {
            "requestContext": {"http": {"method": "GET"}},
            "rawPath": path,
            "queryStringParameters": qs or None,
        }
        resp = lambda_handler(event, None)
        code = int(resp.get("statusCode") or 200)
        body = resp.get("body") or ""
        headers = resp.get("headers") or {"Content-Type": "text/plain; charset=utf-8"}
        self.send_response(code)
        for hk, hv in headers.items():
            self.send_header(hk, hv)
        self.end_headers()
        if isinstance(body, (dict, list)):
            self.wfile.write(json.dumps(body, ensure_ascii=False).encode("utf-8"))
        else:
            self.wfile.write(str(body).encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> None:
    port = int(__import__("os").environ.get("PORT", "8765"))
    httpd = HTTPServer(("127.0.0.1", port), _H)
    print(f"local dashboard http://127.0.0.1:{port}/")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
