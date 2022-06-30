#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

from http.server import HTTPServer, SimpleHTTPRequestHandler
import io
import json
from pathlib import Path
import chevron
import sys

HOST_NAME = "0.0.0.0"
HOST_PORT = 3333

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'merged'
TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'

class SessionServer(SimpleHTTPRequestHandler):
    def _set_headers(self, mimetype="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

    def index(self, fd):
        with open(TEMPLATE_DIR / 'index.mustache') as template:
            fd.write(chevron.render(template, {
                "merged_files": [
                    {
                        "name": f.name
                    }
                    for f in sorted(DATA_DIR.glob('*.json'), reverse=True)
                ]
            }))

    def dump_file(self, fd, fname):

        def template_data(source):
            for speech in source:
                # Only consider speech turns (ignoring comments)
                if 'textContents' not in speech:
                    # No proceedings data, only media.
                    speech_turns = []
                    message = "MEDIA ONLY"
                else:
                    speech_turns = [ turn for turn in speech['textContents'][0]['textBody'] if turn['type'] == 'speech' ]
                    president_turns = [ turn for turn in speech_turns if turn['speakerstatus'].endswith('president') ]
                    if len(president_turns) == len(speech_turns):
                        # Homogeneous president turns
                        message = "PRESIDENT ONLY"
                    else:
                        message = ""
                yield {
                    "index": speech['agendaItem']['speechIndex'],
                    "speech_turns": speech_turns,
                    "message": message
                }

        with open(DATA_DIR / fname, 'r') as f:
            data = json.load(f)

        with open(TEMPLATE_DIR / 'transcript.mustache') as template:
            fd.write(chevron.render(template, {
                "session": fname,
                "speeches": list(template_data(data))
            }))
        return

    def do_GET(self):
        self.out = io.TextIOWrapper(
            self.wfile,
            encoding='utf-8',
            line_buffering=False,
            write_through=True,
        )
        if self.path == '' or self.path == '/':
            self._set_headers()
            self.index(self.out)
            return
        elif self.path.startswith('/view/'):
            fname = self.path.split('/')[2]
            self._set_headers()
            self.dump_file(self.out, fname)
            return
        else:
            SimpleHTTPRequestHandler.do_GET(self)

def main():
    httpserver = HTTPServer((HOST_NAME, HOST_PORT), SessionServer)

    try:
        httpserver.serve_forever()
    except KeyboardInterrupt:
        pass
    httpserver.server_close()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) > 1:
        DATA_DIR = Path(sys.argv[1]).resolve()
    logger.info(f"Listening to {HOST_NAME}:{HOST_PORT}")
    main()
