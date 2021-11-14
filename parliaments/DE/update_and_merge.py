#! /usr/bin/env python3

# Update media files, proceeding files and merge them
import logging
logger = logging.getLogger(__name__)

import argparse
from pathlib import Path
import sys

from scraper.update_media import update_media_directory_period
from scraper.fetch_proceedings import download_plenary_protocols
from merger.merge_session import merge_files_or_dirs

def update_and_merge(args):
    # Download/parse new media data
    update_media_directory_period(args.from_period, args.media_dir, force=args.force, save_raw_data=args.save_raw_data)

    # Download/parse new proceedings data
    download_plenary_protocols(args.proceedings_dir)

    # Produce merged data - output dir is defined in args.output
    merge_files_or_dirs(args.media_dir, args.proceedings_dir, args)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Update media files corresponding to proceeding XML files.")
    parser.add_argument("data_dir", type=str, nargs='?',
                        help="Data directory - mandatory")
    parser.add_argument("--debug", dest="debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--from-period", type=int,
                        help="Period to fetch (mandatory)")
    parser.add_argument("--force", dest="force", action="store_true",
                        default=False,
                        help="Force loading of data for a meeting even if the corresponding file already exists")
    parser.add_argument("--save-raw-data", dest="save_raw_data", action="store_true",
                        default=False,
                        help="Save raw data in JSON format in addition to converted JSON data. It will be an object with 'root' (first page) and 'entries' (all entries for the period/meeting) keys.")
    parser.add_argument("--check", action="store_true",
                        default=False,
                        help="Check mergeability of files")
    parser.add_argument("--unmatched-count", action="store_true",
                        default=False,
                        help="Only display the number of unmatched proceeding items")
    parser.add_argument("--include-all-proceedings", action="store_true",
                        default=False,
                        help="Include all proceedings-issued speeches even if they did not have a match")
    parser.add_argument("--second-stage-matching", action="store_true",
                        default=False,
                        help="Do a second-stage matching using speaker names for non-matching subsequences")
    parser.add_argument("--advanced-rematch", action="store_true",
                        default=False,
                        help="Try harder to realign non-matching proceeding items by skipping some of the items")
    parser.add_argument("--complete", action="store_true",
                        default=False,
                        help="Add all necessary options for a full update (save raw data, include all proceedings)")

    args = parser.parse_args()
    if args.data_dir is None or args.from_period is None:
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel=logging.DEBUG
    logging.basicConfig(level=loglevel)
    if args.complete:
        # Force options
        args.save_raw_data = True
        args.include_all_proceedings = True
    args.data_dir = Path(args.data_dir)
    args.media_dir = args.data_dir / "media"
    args.proceedings_dir = args.data_dir / "proceedings"
    args.output = args.data_dir / "merged"
    update_and_merge(args)
