#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

from pathlib import Path
import statistics

from merge_session import unmatched_count

BASE_DIR = Path(__file__).resolve().parent.parent / 'data'
DATA_DIR = BASE_DIR / 'merged'
PROCEEDINGS_DIR = BASE_DIR / 'proceedings'
MEDIA_DIR = BASE_DIR / 'media'

if __name__ == '__main__':
    print("""Session\tProc size\tMedia size\tUnmatched proceedings\tUnmatched media\tUnmatched media relative""")
    data = []
    for m in sorted(MEDIA_DIR.glob('1*.json')):
        # Find basename
        session = str(m.name)[:5]
        p = PROCEEDINGS_DIR / f'{session}-data.json'
        if p.exists():
            count = unmatched_count(p, m)
            data.append(count)
            print(f"""{session}\t{count['proceedings']}\t{count['media']}\t{count['unmatched_proceedings']}\t{count['unmatched_media']}\t{count['unmatched_media'] / count['media']}""")
        else:
            print(f"""{session}\tUNMATCHED""")
    # Global stats
    size = len(data)
    ratio_list = [ c['unmatched_media'] / c['media'] for c in data ]
    print(f"""Average unmatched media ratio: { statistics.mean(ratio_list) }
Median unmatched media ratio: { statistics.median(ratio_list) }""")
