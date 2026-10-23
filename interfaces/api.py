
import json
from http.server import (
    BaseHTTPRequestHandler,
    HTTPServer
)

from core.agent import OrionAgent
from config import (
    API_HOST,
    API_PORT
)


agent = OrionAgent()


class OrionHandler(
    BaseHTTPRequestHandler
):

    def _send_json(
        self,
        data,
        status=200
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(
            status
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    def do_GET(self):

        if self.path == "/":

            self._send_json(
                {
                    "name": "NEO AI",
                    "status": "online"
                }
            )

            return


        self._send_json(
            {
                "error": "Not found"
            },
            404
        )

    def do_POST(self):

        if self.path != "/chat":

            self._send_json(
                {
                    "error": "Not found"
                },
                404
            )

            return

        try:

            length = int(
                self.headers.get(
                    "Content-Length",
                    "0"
                )
            )

            raw = self.rfile.read(
                length
            )

            data = json.loads(
                raw.decode("utf-8")
            )

            message = str(
                data.get(
                    "message",
                    ""
                )
            ).strip()

            if not message:

                self._send_json(
                    {
                        "error":
                            "Message is required."
                    },
                    400
                )

                return

            response = agent.run(
                message
            )

            self._send_json(
                {
                    "response": response
                }
            )

        except Exception as exc:

            self._send_json(
                {
                    "error": str(exc)
                },
                500
            )

    def log_message(
        self,
        format,
        *args
    ):

        return


def run_server():

    server = HTTPServer(
        (
            API_HOST,
            API_PORT
        ),
        OrionHandler
    )

    print(
        f"NEO AI API running at "
        f"http://{API_HOST}:{API_PORT}"
    )

    try:

        server.serve_forever()

    except KeyboardInterrupt:

        pass

    finally:

        server.server_close()


NeoHandler = OrionHandler
run_api = run_server
run_neo_api = run_server


