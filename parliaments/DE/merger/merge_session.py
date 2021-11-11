#! /usr/bin/env python3

# Merge proceeding and media files

# It takes as input a proceeding file/dir and a media file/dir and outputs a third one with speeches merged.

import logging
logger = logging.getLogger('merge_session' if __name__ == '__main__' else __name__)

import argparse
from copy import deepcopy
import itertools
import json
from pathlib import Path
import re
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

def speaker_cleanup(item):
    if item.get('people'):
        speaker = remove_accents(item['people'][0]['label'].lower()).replace(' von der ', ' ').replace('altersprasident ', '')
    else:
        speaker = None
    return speaker

def get_item_key(item):
    speaker = speaker_cleanup(item)
    title = item['agendaItem']['officialTitle'].strip()
    # Remove trailing .<number>
    title = re.sub('\.\d+$', '', title)
    # Replace MM-NN by only the 1st item (ideally we should generate a sequence MM..NN)
    # title = re.sub('\s(\d+)-\d+$', ' \\1', title)
    return remove_accents(f"{item['electoralPeriod']['number']}-{item['session']['number']} {title} ({speaker})".lower())

def bounded_non_matching_sequences(mapping_sequence):
    """Takes a (proceeding, media) sequence

    Yields sub-sequences of empty proceedings with non-empty
    proceeding boundaries
    """
    def groupkey(tup):
        return "MATCH" if tup[0] is not None else "UNMATCH"

    return itertools.groupby(mapping_sequence, groupkey)

def align_nonmatching_subsequences(mapping_sequence, proceedings, media, options):
    # Mapping_sequence is a list of (proceeding, media) tuples

    # Some of the "proceeding" values may be None, when we could not align them with the whole key.

    # Other option: see https://pypi.org/project/alignment/ for alignment of sub-sequences

    # Categorize sequence. Output a list of [ ("MATCH", [ (p1, m1), (p2, m2), ... ]),
    #                                         ("UNMATCH", [ (None, m5), (None, m6)... ]), ... ]
    categorized_sequences = [ (k, list(seq))
                               for (k, seq) in bounded_non_matching_sequences(mapping_sequence)
                              ]
    #for (k, seq) in non_matching_sequences:
    #    print(f"""{k} - {len(seq)} items""")
    for i, group in enumerate(categorized_sequences):
        category, sequence = group
        if category == 'UNMATCH':
            # We have a sequence with tup[0] (proceeding) == None.

            # Extract from global proceedings list the sequence
            # between the previous matching proc. item and the next matching proc. item
            proc_sequence = list(proceedings)
            if i > 0:
                prev_match = categorized_sequences[i - 1]
                assert prev_match[0] == 'MATCH'
                prev_proc = prev_match[1][-1][0]
                proc_sequence = itertools.dropwhile(lambda p: p['key'] != prev_proc['key'],
                                                    proc_sequence)
            if i < len(categorized_sequences) - 1:
                next_match = categorized_sequences[i + 1]
                assert next_match[0] == 'MATCH'
                next_proc = next_match[1][0][0]
                proc_sequence = itertools.takewhile(lambda p: p['key'] != next_proc['key'],
                                                    proc_sequence)
            # We should now have a corresponding proceedings sequence that we must align
            proc_sequence = list(proc_sequence)
            logger.debug(f"--- {len(proc_sequence)} / {len(sequence)} non matching items -----")
            for m, p in itertools.zip_longest(sequence, proc_sequence):
                logger.debug("%s\t%s" % (m[1]['people'][0]['label'] if m else 'None',
                                  p['people'][0]['label'] if p else 'None'))
            # Now align items
            for p, m in sequence:
                # p is None since we are in an UNMATCH group
                key = speaker_cleanup(m)
                # Try to find a matching name in proc_sequence
                matching_proc = None
                if proc_sequence:
                    p = proc_sequence[0]
                    if speaker_cleanup(p) == key:
                        # Matching speaker name
                        matching_proc = proc_sequence.pop(0)
                    elif options.advanced_rematch and len(proc_sequence) > 1:
                        # Try one item further
                        p = proc_sequence[1]
                        if speaker_cleanup(p) == key:
                            # Matching speaker name
                            matching_proc = p
                            # Remove 2 items
                            proc_sequence.pop(0)
                            proc_sequence.pop(0)

                yield matching_proc, m
        else:
            for tup in sequence:
                yield tup

def matching_items(proceedings, media, options):
    """Return a list of (proceeding, mediaitem) items that match.
    """
    # Build a dict for proceedings, indexed by key
    procdict = {}
    mediadict = {}
    for label, source, itemdict in ( ('proceedings', proceedings, procdict),
                                     ('media', media, mediadict) ):
        for item in source:
            # Get standard key
            item['key'] = get_item_key(item)
            if item['key'] in itemdict:
                # Duplicate key - add a #N to the key to differenciate
                # We do not use item['agendaItem']['speechIndex']
                # because we want to use the relative appearing order of items.
                n = 1
                while True:
                    newkey = f"{item['key']} #{n}"
                    if newkey not in itemdict:
                        break
                    n = n + 1
                item['key'] = newkey
            itemdict[item['key']] = item

    # Determine all key-based matching items
    output = [ (procdict.get(m['key']), m) for m in media ]

    if options.second_stage_matching or options.advanced_rematch:
        # Using matching items as landmarks, try to align remaining
        # sequences based on speaker names matching
        output = list(align_nonmatching_subsequences(output, proceedings, media, options))

    output_proceeding_keys = set( p['key']
                                  for p, m in output
                                  if p is not None )

    if options.include_all_proceedings:
        # Add proceeding items with no matching media items - in speechIndex order
        proc_items = ( p for p in proceedings if p['key'] not in output_proceeding_keys )
        output.extend((item, None) for item in proc_items)
    return output

def diff_files(proceedings_file, media_file, options):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    #width = int(int(os.environ.get('COLUMNS', 80)) / 2)
    width = 60
    left = "Proceeding"
    right = "Media"
    print(f"""{left.ljust(width)} {right}""")
    for (p, m) in matching_items(proceedings, media, options):
        left = '[[[ None ]]]' if p is None else p['key']
        right = '[[[ None ]]]' if m is None else m['key']
        print(f"""{left.ljust(width)} {right}""")

def unmatched_count(proceedings_file, media_file, options):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    matching = matching_items(proceedings, media, options)
    unmatched_proceedings = [ p for (p, m) in matching if m is None ]
    unmatched_media = [ m for (p, m) in matching if p is None ]
    return {
        'proceedings_file': str(proceedings_file),
        'media_file': str(media_file),
        'proceedings_count': len(proceedings),
        'media_count': len(media),
        'unmatched_proceedings': len(unmatched_proceedings),
        'unmatched_media': len(unmatched_media)
    }

def merge_data(proceedings, media, options):
    """Merge data structures.

    If no match is found for a proceedings, we will dump the
    proceedings as-is.
    """
    return [
        merge_item(p, m)
        for (p, m) in matching_items(proceedings, media, options)
    ]

def matching_proceeding(mediafile: Path, proceedings_dir: Path) -> Path:
    p = proceedings_dir / mediafile.name.replace('media', 'data')
    if p.exists():
        return p
    else:
        return None

def build_pairs(proceedings_dir, media_dir):
    for m in sorted(media_dir.glob('[0-9]*.json')):
        # Try to find the matching proceedings file
        p = matching_proceeding(m, proceedings_dir)
        yield (p, m)

def merge_files(proceedings_file, media_file, options):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    # Order media, according to dateStart
    return merge_data(proceedings, media, options)

def merge_files_or_dirs(media: Path, proceedings: Path, args):
    pairs = [ (proceedings, media) ]
    if media.is_dir() and proceedings.is_dir():
        # Directory version. Build the pairs data structure
        pairs = build_pairs(proceedings, media)
    elif media.is_file() and proceedings.is_dir():
        # Try to find the matching proceedings given a media file.
        pairs = [ (matching_proceeding(media, proceedings), media) ]
    elif media.is_dir() and proceedings.is_file():
        logger.error("Cannot merge data without a media file")
        sys.exit(1)

    if args.unmatched_count:
        is_first = True
        print('[')
        for (p, m) in pairs:
            if p is None:
                continue
            if not is_first:
                print(",")
            print(json.dumps(unmatched_count(p, m, args), indent=2))
            is_first = False
        print(']')
        sys.exit(0)
    elif args.check:
        for (p, m) in pairs:
            if p is None:
                continue
            print(f"* Difference between {p.name} and {m.name}")
            diff_files(p, m, args)
            print("\n")
    else:
        for (p, m) in pairs:
            if p is None:
                logger.debug(f"Media {m.name} without proceeding. Copying file")
                data = json.loads(m.read_text())
            else:
                logger.debug(f"Merging {p.name} and {m.name}")
                data = merge_files(p, m, args)
            if args.output:
                output_dir = Path(args.output)
                if not output_dir.is_dir():
                    output_dir.mkdir(parents=True)
                period = data[0]['electoralPeriod']['number']
                meeting = data[0]['session']['number']
                filename = f"{period}{str(meeting).rjust(3, '0')}-merged.json"
                logger.debug(f"Saving into {filename}")
                with open(output_dir / filename, 'w') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, sys.stdout, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge proceedings and media file.")
    parser.add_argument("proceedings_file", type=str, nargs='?',
                        help="Proceedings file or directory")
    parser.add_argument("media_file", type=str, nargs='?',
                        help="Media file or directory")
    parser.add_argument("--debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--output", metavar="DIRECTORY", type=str,
                        help="Output directory - if not specified, output with be to stdout")
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
                        help="Try harder to realign non-matching proceedin items by skipping some of the items")

    args = parser.parse_args()
    if args.media_file is None or args.proceedings_file is None:
        parser.print_help()
        sys.exit(1)
    loglevel = logging.INFO
    if args.debug:
        loglevel=logging.DEBUG
    logging.basicConfig(level=loglevel)

    merge_files_or_dirs(Path(args.media_file), Path(args.proceedings_file), args)
