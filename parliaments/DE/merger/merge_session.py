#! /usr/bin/env python3

# Merge 2 session files (list of speeches)

# It takes as input 2 session JSON files and outputs a third one with speeches merged.

import logging
logger = logging.getLogger(__name__)

from copy import deepcopy
import json
import sys
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def merge_item(proceeding, mediaitem):
    output = deepcopy(proceeding)
    for key, value in mediaitem.items():
        if key in proceeding:
            # Existing key. Check for embedded object.
            print(key, value)
    return output

def get_item_key(item):
    if item['people']:
        speaker = item['people'][0]['label']
    else:
        speaker = None

    return remove_accents(f"{item['electoralPeriod']['number']}-{item['session']['number']} {item['agendaItem']['officialTitle']} ({speaker})".lower())

def matching_items(proceedings, media):
    """Return a list of (proceeding, mediaitem) items that match.
    """
    for item in (*proceedings, *media):
        item['key'] = get_item_key(item)

    # Build key sets
    mediakeys = set(m['key'] for m in media)
    proceedingkeys = set(p['key'] for p in proceedings)

    # Build a dict for media indexed by key
    mediadict = {}
    for m in media:
        if m['key'] in m:
            logger.error(f"Conflict in media key: {m['key']}")
            continue
        mediadict[m['key']] = m

    output = [ (p, mediadict.get(p['key'])) for p in proceedings ]

    # Add media items with no matching proceeding items
    output.extend( (None, mediadict.get(k)) for k in sorted(mediakeys - proceedingkeys) )
    return output

def diff_files(proceedings_file, media_file):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    #width = int(int(os.environ.get('COLUMNS', 80)) / 2)
    width = 60
    for (p, m) in matching_items(proceedings, media):
        left = '[[[ None ]]]' if p is None else p['key']
        right = '[[[ None ]]]' if m is None else m['key']
        print(f"""{left.ljust(width)} {right}""")

def merge_data(proceedings, media):
    # Note: unfinished code - we need to consolidate data first.
    return [ merge_item(p, m)
             for (p, m) in matching_items(proceedings, media) ]

def merge_files(proceedings_file, media_file):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    # Order media, according to dateStart
    return merge_data(proceedings, media)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.warning(f"Syntax: {sys.argv[0]} proceedings_file.json media_file.json")
        sys.exit(1)

    #data = merge_files(sys.argv[1], sys.argv[2])
    #json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    diff_files(sys.argv[1], sys.argv[2])

