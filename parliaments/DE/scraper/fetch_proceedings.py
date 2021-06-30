#! /usr/bin/env python3

# Fetch Proceedings for Bundestag
# It must be given an output directory (like examples/proceedings) and will fetch only missing files.

# Adapted from
# https://blog.oliverflasch.de/german-plenary-proceedings-as-a-nlp-testbed/

import logging
logger = logging.getLogger(__name__)

import argparse
import lxml.html
import os
from pathlib import Path
import sys
import urllib.request
import urllib3

SERVER_ROOT = "https://www.bundestag.de"

def download_plenary_protocols(destination_dir: str, fullscan: bool = False):
    dest = Path(destination_dir)
    # Create directory if necessary
    if not dest.is_dir():
        dest.mkdir(parents=True)
    http = urllib3.PoolManager()
    index_file = open(dest / "index.txt", 'wt+')
    offset = 0
    while True:
        logger.debug(f"Fetching RSS with offset {offset}")
        response = http.request("GET", f"{SERVER_ROOT}/ajax/filterlist/de/services/opendata/543410-543410?noFilterSet=true&offset={offset}")
        parsed = lxml.html.fromstring(response.data)
        link_count = 0
        for link in parsed.getiterator(tag="a"):
            link_href = link.attrib["href"]
            link_count += 1
            basename = os.path.basename(link_href)
            filename = dest / basename
            if filename.exists():
                # Existing file.
                if not fullscan:
                    logger.info("Found 1 cached file. Stopping.")
                    return
            else:
                # Downdload file
                file_url = f"{SERVER_ROOT}{link_href}"
                logger.info(f"downloading URL {file_url}")
                urllib.request.urlretrieve(file_url, filename)
                # Add URL reference to index.txt
                index_file.write(f"{basename} {file_url}\n")
        if link_count == 0:
            # Empty file, end of data
            break
        offset += link_count
    index_file.close()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch Bundestag RSS feed.")
    parser.add_argument("output_dir", metavar="output_dir", type=str, nargs='?',
                        help="Output directory")
    parser.add_argument("--debug", dest="debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--full-scan", dest="fullscan", action="store_true",
                        default=False,
                        help="Do a full scan of the RSS feed (else we stop at the first existing file)")
    args = parser.parse_args()
    if args.output_dir is None:
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel=logging.DEBUG
    logging.basicConfig(level=loglevel)
    download_plenary_protocols(args.output_dir, args.fullscan)
    
