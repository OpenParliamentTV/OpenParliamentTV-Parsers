#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

import argparse
from pathlib import Path
import statistics
import sys

from merge_session import unmatched_count

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Output stats on matched info.")
    parser.add_argument("media", type=str, nargs='+',
                        help="Media files (json)")
    parser.add_argument("--debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--include-all-proceedings", action="store_true",
                        default=True,
                        help="Include all proceedings-issued speeches even if they did not have a match")
    parser.add_argument("--second-stage-matching", action="store_true",
                        default=False,
                        help="Do a second-stage matching using speaker names for non-matching subsequences")
    parser.add_argument("--advanced-rematch", action="store_true",
                        default=False,
                        help="Try harder to realign non-matching proceedin items by skipping some of the items")

    args = parser.parse_args()

    print("""Session\tProc#\tMedia#\tUnmatched proceedings\tUnmatched media\tUnmatched media relative""")
    data = []

    for m in args.media:
        media = Path(m)
        # Find basename
        session = str(media.name)[:5]
        # Consider a standard directory layout
        proceeding = media.parent.parent / 'proceedings' / f'{session}-data.json'
        if proceeding.exists():
            count = unmatched_count(proceeding, media, args)
            data.append(count)
            print(f"""{session}\t{count['proceedings_count']}\t{count['media_count']}\t{count['unmatched_proceedings_count']}\t{count['unmatched_media_count']}\t{count['unmatched_media_count'] / count['media_count']}""")
        else:
            if not proceeding.parent.exists():
                # Wrong directory layout
                logger.error("Cannot find proceedings directory {proceeding.parent}")
                sys.exit(1)
            print(f"""{session}\tUNMATCHED""")
    # Global stats
    size = len(data)
    ratio_list = [ c['unmatched_media_count'] / c['media_count'] for c in data ]
    print(f"""Average unmatched media ratio: { statistics.mean(ratio_list) }
Median unmatched media ratio: { statistics.median(ratio_list) }""")
