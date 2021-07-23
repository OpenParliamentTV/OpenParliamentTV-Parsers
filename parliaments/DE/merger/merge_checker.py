#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

from http.server import HTTPServer, SimpleHTTPRequestHandler
import io
import json
from pathlib import Path
import sys

HOST_NAME = "0.0.0.0"
HOST_PORT = 3333

DATA_DIR = Path(__file__).resolve().parent.parent / 'data' / 'merged'

class SessionServer(SimpleHTTPRequestHandler):
    def _set_headers(self, mimetype="text/html; charset=utf-8"):
        self.send_response(200)
        self.send_header('Content-type', mimetype)
        self.end_headers()

    def index(self, fd):
        data = "\n".join(f"""<li><a href="view/{f.name}">{f.name}</a></li>""" for f in sorted(DATA_DIR.glob('*.json')))
        fd.write(f"""<html><body><h1>Index</h1><ul>{data}</ul></body></html>""")

    def dump_file(self, fd, fname):
        datafile = DATA_DIR / fname
        with open(datafile, 'r') as f:
            data = json.load(f)
        fd.write("""<html><style>
        .status { font-style: italic; font-weight: bold; }
            .speaker { font-style: italic; }
            .text { color: #999; }
            .player { position: fixed; top: 0; right: 0; width: 320px; height: 200px;  }
            .menu { position: fixed; bottom: 0; right: 0; }
            </style>
            <body>
            <p class="menu"><a href="/">Home</a></p>
            <video controls autoplay class="player"></video>
            <div class="transcript">
            """)
        for speech in data:
            # Only consider speech turns (ignoring comments)
            if 'textContents' not in speech:
                # No proceedings data, only media.
                speech_turns = []
                msg = "MEDIA ONLY"
            else:
                speech_turns = [ turn for turn in speech['textContents'][0]['textBody'] if turn['type'] == 'speech' ]
                president_turns = [ turn for turn in speech_turns if turn['speakerstatus'].endswith('president') ]
                if len(president_turns) == len(speech_turns):
                    # Homogeneous president turns
                    msg = "PRESIDENT ONLY"
                else:
                    msg = ""
            fd.write(f"""<h1><strong>{speech['agendaItem']['speechIndex']}</strong> {speech['agendaItem']['officialTitle']} <em>{msg}</em><a class="videolink" href="{speech['media']['videoFileURI']}">URI</a></h1>\n""")
            for turn in speech_turns:
                fd.write(f"""<p><span class="status">{turn['speakerstatus']}</span> <span class="speaker">{turn['speaker']}</span> <span class="text">{turn['text']}</span></p>""")
        fd.write("""
            </div>
            <script>
            document.querySelectorAll(".videolink").forEach(link => {
            link.addEventListener("click", e => {
                    e.preventDefault();
                    console.log(e.target);
                    let url = e.target.href;
                    document.querySelector(".player").src = url;
                  })
            });
            </script>
            </body></html>
            """)
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
