#! /usr/bin/env python3

# Update a media directory

import logging
logger = logging.getLogger(__name__)

import argparse
from pathlib import Path
import re
import sys

# Allow relative imports if invoked as a script
# From https://stackoverflow.com/a/65780624/2870028
if __package__ is None:
    module_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(module_dir.parent))
    __package__ = module_dir.name

from .fetch_media import download_meeting_data, download_data, get_filename

def update_media_directory(proc_dir, media_dir, force=False, save_raw_data=False):
    for proc in sorted(proc_dir.glob('*-data.xml')):
        basename = proc.name
        period = basename[:2]
        meeting = basename[2:5]
        filename = get_filename(period, meeting)
        if force or not (media_dir / filename).exists():
            logger.debug(f"Loading {period}-{meeting} data into {filename}")
            download_data(period, meeting, media_dir, save_raw_data=save_raw_data)

def update_media_directory_period(period, media_dir, force=False, save_raw_data=False):
    # Fetch root page for period. This will allow us to determine the
    # most recent meeting number and then try to fetch them when needed
    rootinfo = download_meeting_data(period, media_dir, root_only=True)
    if not rootinfo['entries']:
        logger.error(f"No entries for period {period} - maybe a server timeout?")
        return
    # Get latest Sitzung/meeting number from first entry title
    latest_title = rootinfo['entries'][0]['title']
    numbers = re.findall('\((\d+)\.\sSitzung', latest_title)
    if not numbers:
        logger.error(f"Cannot determine latest meeting number from latest entry: {latest_title}")
        return
    latest_number = int(numbers[0])
    logger.info(f"Download period {period} meetings from {latest_number} downwards" )
    for meeting in range(latest_number, 0, -1):
        filename = get_filename(period, meeting)
        # We ignore cache if the force option is given, but also for
        # the latest meeting, since we may be updating a live meeting
        # which is updated throughout the session.  We assume here
        # that once a new session has begun, the previous ones are
        # "solid" so we can use cached information.
        force = force or meeting == latest_number
        if (force
            or not (media_dir / filename).exists()):
            logger.debug(f"Loading {period}-{meeting} data into {filename}")
            download_data(period, meeting, media_dir, save_raw_data=save_raw_data, force=force)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Update media files corresponding to proceeding XML files.")
    parser.add_argument("media_dir", type=str, nargs='?',
                        help="Media directory (output)")
    parser.add_argument("--debug", dest="debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--from-proceedings", type=str,
                        help="Proceedings directory (input)")
    parser.add_argument("--from-period", type=int,
                        help="Period to fetch")
    parser.add_argument("--force", dest="force", action="store_true",
                        default=False,
                        help="Force loading of data for a meeting even if the corresponding file already exists")
    parser.add_argument("--save-raw-data", dest="save_raw_data", action="store_true",
                        default=False,
                        help="Save raw data in JSON format in addition to converted JSON data. It will be an object with 'root' (first page) and 'entries' (all entries for the period/meeting) keys.")
    args = parser.parse_args()
    if args.media_dir is None or (args.from_proceedings is None
                                  and args.from_period is None):
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel=logging.DEBUG
    logging.basicConfig(level=loglevel)
    if args.from_proceedings:
        update_media_directory(Path(args.from_proceedings), Path(args.media_dir), force=args.force, save_raw_data=args.save_raw_data)
    elif args.from_period:
        update_media_directory_period(args.from_period, Path(args.media_dir), force=args.force, save_raw_data=args.save_raw_data)
