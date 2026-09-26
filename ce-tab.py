#!/usr/bin/env python3

import json
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer,
)


current_url = ""


HTML = r"""
<!doctype html>

<html>
<head>
    <meta charset="utf-8">

    <title>Compiler Explorer Relay</title>

    <style>
        body {
            font-family: sans-serif;
            max-width: 700px;
            margin: 40px auto;
        }

        button {
            font-size: 16px;
            padding: 10px 20px;
        }

        code {
            word-break: break-all;
        }
    </style>
</head>

<body>

<h2>Compiler Explorer Relay</h2>

<p>
    Keep this page open.
</p>

<p>
    Click the button once to create the reusable
    Compiler Explorer tab.
</p>

<button onclick="openCompilerExplorer()">
    Open Compiler Explorer
</button>

<p>
Current state:
</p>

<code id="url">waiting...</code>

<script>
let ceWindow = null;
let lastUrl = "";

function openCompilerExplorer() {
    ceWindow = window.open(
        "http://localhost:10240",
        "local-compiler-explorer"
    );
}

async function check() {
    try {
        const response =
            await fetch("/current", {
                cache: "no-store"
            });

        const data =
            await response.json();

        if (!data.url) {
            return;
        }

        document
            .getElementById("url")
            .textContent = data.url;

        if (data.url === lastUrl) {
            return;
        }

        lastUrl = data.url;

        if (
            !ceWindow ||
            ceWindow.closed
        ) {
            return;
        }

        ceWindow.location.href =
            data.url;

    } catch (_) {
    }
}

setInterval(check, 500);
</script>

</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def send_json(self, obj):
        data = json.dumps(obj).encode()

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "application/json",
        )

        self.send_header(
            "Cache-Control",
            "no-store",
        )

        self.send_header(
            "Content-Length",
            str(len(data)),
        )

        self.end_headers()

        self.wfile.write(data)

    def do_GET(self):
        global current_url

        if self.path == "/":
            data = HTML.encode()

            self.send_response(200)

            self.send_header(
                "Content-Type",
                "text/html; charset=utf-8",
            )

            self.send_header(
                "Content-Length",
                str(len(data)),
            )

            self.end_headers()

            self.wfile.write(data)

            return

        if self.path == "/current":
            self.send_json(
                {
                    "url": current_url,
                }
            )

            return

        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        global current_url

        if self.path != "/update":
            self.send_response(404)
            self.end_headers()
            return

        length = int(
            self.headers.get(
                "Content-Length",
                "0",
            )
        )

        body = self.rfile.read(length)

        data = json.loads(body.decode("utf-8"))

        current_url = data["url"]

        self.send_json(
            {
                "ok": True,
            }
        )

    def log_message(
        self,
        format,
        *args,
    ):
        pass


print("Compiler Explorer relay running:")
print("http://127.0.0.1:8123")

HTTPServer(
    ("127.0.0.1", 8123),
    Handler,
).serve_forever()
