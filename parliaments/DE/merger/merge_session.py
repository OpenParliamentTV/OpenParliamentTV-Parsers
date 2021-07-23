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
        speaker = remove_accents(item['people'][0]['label'].lower()).replace(' von der ', ' ').replace('altersprasident ', '')
    else:
        speaker = None

    return remove_accents(f"{item['electoralPeriod']['number']}-{item['session']['number']} {item['agendaItem']['officialTitle']} ({speaker})".lower())

def matching_items(proceedings, media, include_all_proceedings=False):
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

    output = [ (procdict.get(m['key']), m) for m in media ]

    output_proceeding_keys = set( p['key']
                                  for p, m in output
                                  if p is not None )

    if include_all_proceedings:
        # Add proceeding items with no matching media items - in speechIndex order
        proc_items = ( p for p in proceedings if p['key'] not in output_proceeding_keys )
        output.extend((item, None) for item in proc_items)
    return output

def diff_files(proceedings_file, media_file):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    #width = int(int(os.environ.get('COLUMNS', 80)) / 2)
    width = 60
    left = "Media"
    right = "Proceeding"
    print(f"""{left.ljust(width)} {right}""")
    for (p, m) in matching_items(proceedings, media):
        left = '[[[ None ]]]' if m is None else m['key']
        right = '[[[ None ]]]' if p is None else p['key']
        print(f"""{left.ljust(width)} {right}""")

def merge_data(proceedings, media, include_all_proceedings=False):
    """Merge data structures.

    If no match is found for a proceedings, we will dump the
    proceedings as-is.
    """
    return [
        merge_item(p, m)
        for (p, m) in matching_items(proceedings, media, include_all_proceedings=False)
    ]

def merge_files(proceedings_file, media_file, include_all_proceedings=False):
    with open(proceedings_file) as f:
        proceedings = json.load(f)
    with open(media_file) as f:
        media = json.load(f)
    # Order media, according to dateStart
    return merge_data(proceedings, media, include_all_proceedings=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Merge proceedings and media file.")
    parser.add_argument("proceedings_file", type=str, nargs='?',
                        help="Proceedings file")
    parser.add_argument("media_file", type=str, nargs='?',
                        help="Media file")
    parser.add_argument("--debug", action="store_true",
                        default=False,
                        help="Display debug messages")
    parser.add_argument("--dump", action="store_true",
                        help="Dump debugging information (and do not output data)")
    parser.add_argument("--dump-html", action="store_true",
                        help="Dump debugging information as html (implies --dump)")
    parser.add_argument("--output", metavar="DIRECTORY", type=str,
                        help="Output directory - if not specified, output with be to stdout")
    parser.add_argument("--check", action="store_true",
                        default=False,
                        help="Check mergeability of files")
    parser.add_argument("--include-all-proceedings", action="store_true",
                        default=False,
                        help="Include all proceedings-issued speeches even if they did not have a match")
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
        data = merge_files(args.proceedings_file, args.media_file, args.include_all_proceedings)
        if args.dump or args.dump_html:
            if args.dump_html:
                print("""<html><style>
                .status { font-style: italic; font-weight: bold; }
                .speaker { font-style: italic; }
                .text { color: #999; }
                .player { position: fixed; top: 0; right: 0; width: 320px; height: 200px;  }
                </style>
                <body>
                <video controls autoplay class="player"></video>
                """)
            for speech in data:
                # Only consider speech turns (ignoring comments)
                if 'textContents' not in speech:
                    # No proceedings data, only media.
                    speech_turns = []
                    msg = "MEDIA ONLY"
                else:
                    speech_turns = [ turn for turn in speech['textContents'][0]['textBody'] if turn['type'] == 'speech' ]
                    president_turns = [ turn for turn in speech_turns if turn['speakerstatus'].endswith('president') ]
                    if len(president_turns) == len(speech_turns):
                        # Homogeneous president turns
                        msg = " --- TO BE MERGED?"
                    else:
                        msg = ""
                if args.dump_html:
                    print(f"""<h1><strong>{speech['agendaItem']['speechIndex']}</strong> {speech['agendaItem']['officialTitle']} <em>{msg}</em><a class="videolink" href="{speech['media']['videoFileURI']}">URI</a></h1>""")
                    for turn in speech_turns:
                        print(f"""<p><span class="status">{turn['speakerstatus']}</span> <span class="speaker">{turn['speaker']}</span> <span class="text">{turn['text']}</span></p>""")
                else:
                    print(f"{speech['agendaItem']['speechIndex']} {speech['agendaItem']['officialTitle']} {msg} {speech['media']['videoFileURI']}")
                    for turn in speech_turns:
                        print(f"    {turn['speakerstatus']} {turn['speaker']}")

            if args.dump_html:
                print("""
                <script>
                document.querySelectorAll(".videolink").forEach(link => {
                link.addEventListener("click", e => {
                        e.preventDefault();
                        console.log(e.target);
                        let url = e.target.href;
                        document.querySelector(".player").src = url;
                      })
                });
                </script>
                </body></html>
                """)
            sys.exit(0)
        elif args.output:
            output_dir = Path(args.output)
            if not output_dir.is_dir():
                output_dir.mkdir(parents=True)
            period = data[0]['electoralPeriod']['number']
            meeting = data[0]['session']['number']
            filename = f"{period}{str(meeting).rjust(3, '0')}-merged.json"
            with open(output_dir / filename, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
