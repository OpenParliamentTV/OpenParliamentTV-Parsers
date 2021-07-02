#! /usr/bin/env python3

# Merge 2 session files (list of speeches)

# It takes as input 2 session JSON files and outputs a third one with speeches merged.

import logging
logger = logging.getLogger(__name__)

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import unicodedata

def remove_accents(input_str):
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)])

def merge_item(proceeding, mediaitem):
    # Non-matching case - return the unmodified value
    if proceeding is None:
        return mediaitem
    if mediaitem is None:
        return proceeding

    # We have both items - copy media data into proceedings
    # Make a copy of the proceedings file
    output = deepcopy(proceeding)

    # Copy relevant data from mediaitem
    output['agendaItem']['title'] = mediaitem['agendaItem']['title']
    output['dateStart'] = mediaitem['dateStart']
    output['dateEnd'] = mediaitem['dateEnd']
    output['media'] = mediaitem['media']

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

    # Build a dict for proceedings indexed by key
    procdict = {}
    for p in proceedings:
        if p['key'] in procdict:
            # Let's nullify the conflicting key, so that we do not merge it by mistake
            procdict[p['key']] = None
            logger.error(f"Conflict in proceedings key: {p['key']}")
            continue
        procdict[p['key']] = p

    output = [ (procdict.get(m['key']), m) for m in media ]

    # Add proceeding items with no matching media items - in speechIndex order
    proc_items = sorted( [ procdict.get(k) for k in (proceedingkeys - mediakeys) ],
                         key=lambda p: p['agendaItem']['speechIndex'])
    output.extend((item, None) for item in proc_items)
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
    """Merge data structures.

    If no match is found for a proceedings, we will dump the
    proceedings as-is.
    """
    return [
        merge_item(p, m)
        for (p, m) in matching_items(proceedings, media)
    ]

def merge_files(proceedings_file, media_file):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    # Order media, according to dateStart
    return merge_data(proceedings, media)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge proceedings and media file.")
    parser.add_argument("proceedings_file", type=str, nargs='?',
                        help="Proceedings file")
    parser.add_argument("media_file", type=str, nargs='?',
                        help="Media file")
    parser.add_argument("--debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--output", metavar="DIRECTORY", type=str,
                        help="Output directory - if not specified, output with be to stdout")
    parser.add_argument("--check", action="store_true",
                        default=False,
                        help="Check mergeability of files")
    args = parser.parse_args()
    if args.media_file is None or args.proceedings_file is None:
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel=logging.DEBUG
    logging.basicConfig(level=loglevel)

    if args.check:
        diff_files(args.proceedings_file, args.media_file)
    else:
        data = merge_files(args.proceedings_file, args.media_file)
        if args.output:
            output_dir = Path(args.output)
            if not output_dir.is_dir():
                output_dir.mkdir(parents=True)
            period = data[0]['electoralPeriod']['number']
            meeting = data[0]['session']['number']
            filename = f"{period}{meeting.rjust(3, '0')}-merged.json"
            with open(output_dir / filename, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
