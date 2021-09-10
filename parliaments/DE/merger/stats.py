#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

import json
from pathlib import Path
import sys

from merge_session import unmatched_count, diff_files

BASE_DIR = Path(__file__).resolve().parent.parent / 'data'
DATA_DIR = BASE_DIR / 'merged'
PROCEEDINGS_DIR = BASE_DIR / 'proceedings'
MEDIA_DIR = BASE_DIR / 'media'

if __name__ == '__main__':
    pcounts = []
    mcounts = []
    print("""Session\tProc size\tMedia size\tUnmatched proceedings\tUnmatched media""")
    for m in sorted(MEDIA_DIR.glob('1*.json')):
        # Find basename
        session = str(m.name)[:5]
        p = PROCEEDINGS_DIR / f'{session}-data.json'
        if p.exists():
            count = unmatched_count(p, m)
            print(f"""{session}\t{count['proceedings']}\t{count['media']}\t{count['unmatched_proceedings']}\t{count['unmatched_media']}""")
            pcounts.append(count['proceedings'])
            mcounts.append(count['media'])
        else:
            print(f"""{session}\tUNMATCHED""")
    # Global stats
