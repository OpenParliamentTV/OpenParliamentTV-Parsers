#! /usr/bin/env python3

# Fetch Media items for Bundestag

# It will fetch and aggregate paginated data, either for a whole period or for a specific period + meeting

# It outputs data to stdout, or
# it can be given an output directory (like examples/media) through the --output option

# For reference, base URLs are like
# http://webtv.bundestag.de/player/macros/bttv/podcast/video/plenar.xml?period=17&meetingNumber=190

import logging
logger = logging.getLogger(__name__)

import argparse
import feedparser
import json
from pathlib import Path
import sys

try:
    from parsers.media2json import parse_media_data
except ModuleNotFoundError:
    # Module not found. Tweak the sys.path
    base_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(base_dir))
    from parsers.media2json import parse_media_data

ROOT_URL = "http://webtv.bundestag.de/player/macros/bttv/podcast/video/plenar.xml"
SERVER_ROOT = "https://www.bundestag.de"

def get_latest():
    latest = feedparser.parse(ROOT_URL)
    return latest

def next_rss(data):
    feed = data.get('feed')
    if feed is None:
        return None
    links = feed.get('links')
    if not links:
        return None
    nexts = [ l for l in links if l.get('rel') == 'next' ]
    if nexts:
        return nexts[0]['href']
    else:
        return None

def download_meeting_data(period: int, number: int = None, root_only=False):
    """Download data for a given meeting, handling pagination.
    """
    if number is None:
        root_url = f"{ROOT_URL}?period={period}"
    else:
        root_url = f"{ROOT_URL}?period={period}&meetingNumber={number}"

    root = feedparser.parse(root_url)
    logger.debug(f"Status {root['status']}")
    if root['status'] != 200:
        # Frequent error from server. We should retry. For the moment,
        # this will be done by re-running the script, since it will
        # only update necessary files.
        logger.warning(f"Download error ({root['status']}) - ignoring entries")
        return { 'root': root, 'entries': [] }
    entries = root['entries']
    if root_only:
        # We only want root. Populate entries anyway, because this
        # allows the calling layer to test for ['entries'] emptiness
        # to know if something went wrong.
        return { 'root': root, 'entries': root['entries'] }
    next_url = next_rss(root)
    while next_url:
        logger.info(f"Downloading {next_url}")
        data = feedparser.parse(next_url)
        logger.debug(f"Status {data['status']} - {len(data['entries'])} entries")
        if data['status'] != 200:
            # Frequent error from server. Ignore the already fetched entries.
            # We should retry. For the moment,
            # this will be done by re-running the script, since it will
            # only update necessary files.
            logger.warning(f"Download error ({data['status']}) - ignoring entries")
            return { 'root': root, 'entries': [] }

        entries.extend(data['entries'])
        next_url = next_rss(data)
    return { "root": root,
             "entries": entries }

def get_filename(period, meeting=None):
    if meeting is None:
        # Only period is specified
        return f"{period}-all-media.json"
    else:
        return f"{period}{str(meeting).rjust(3, '0')}-media.json"

def download_data(period, meeting=None, output=None, save_raw_data=False, force=False):
    """Download data for a given meeting.

    In case of error, parsed_data will be [].

    If a raw data file is present, it will be used, except if the
    force option is set to True.

    You can test for the status of the fetch query by testing
    raw_data['root']['status'] : it is 200 in case of success. The
    server often returns a 503.

    Returns a tuple (raw_data, parsed_data).

    """
    filename = get_filename(period, meeting)
    raw_filename = f"raw-{filename}"
    if output:
        output_dir = Path(output)
        if not output_dir.is_dir():
            output_dir.mkdir(parents=True)
    try:
        if output and (output_dir / raw_filename).exists() and not force:
            # There is a raw data dump. Use it rather than downloading
            # it again.
            logger.warning(f"Using data dump {raw_filename}")
            with open(output_dir / raw_filename) as f:
                raw_data = json.load(f)
        else:
            raw_data = download_meeting_data(period, meeting)
        if not raw_data['entries']:
            # No entries - something must have gone wrong. Bail out
            # import IPython; IPython.embed()
            return raw_data, []
        data = parse_media_data(raw_data)
    except:
        logger.exception("Error - going into debug mode")
        # import IPython; IPython.embed()

    logger.debug(f"Saving {len(data)} entries into {filename}")
    if output:
        with open(output_dir / filename, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if save_raw_data and not (output_dir / raw_filename).exists():
            with open(output_dir / raw_filename, 'w') as f:
                json.dump(raw_data, f, indent=2, ensure_ascii=False)
    else:
        # No output dir option - dump to stdout
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    return raw_data, data

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fetch Bundestag Media RSS feed.")
    parser.add_argument("period", metavar="period", type=str, nargs='?',
                        help="Period number (19 is the latest)")
    parser.add_argument("meeting", metavar="meeting", type=str, nargs='?',
                        help="Meeting number")
    parser.add_argument("--output", type=str, default="",
                        help="Output directory")
    parser.add_argument("--save-raw-data", dest="save_raw_data", action="store_true",
                        default=False,
                        help="Save raw data in JSON format in addition to converted JSON data. It will be an object with 'root' (first page) and 'entries' (all entries for the period/meeting) keys.")
    parser.add_argument("--debug", dest="debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--full-scan", dest="fullscan", action="store_true",
                        default=False,
                        help="Do a full scan of the RSS feed (else we stop at the first existing file)")
    args = parser.parse_args()
    if args.period is None:
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    download_data(args.period, args.meeting, args.output, args.save_raw_data)
