#! /usr/bin/env python3

# Convert RSS index file from http://webtv.bundestag.de into JSON with
# fields defined for OpenParliamentTV

import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
import feedparser
import json
import os
import sys
from typing import Final
from urllib.parse import urlparse, parse_qs

# Constants used for basic integrity checking: If these values are not
# present in the source data, then something must have changed and the
# parser should be checked anyway.
FEED_SUBTITLE: Final = 'Deutscher Bundestag'
FEED_AUTHOR_EMAIL: Final = 'mail@bundestag.de'

def parse_rss(filename: str) -> dict:
    """Parse a RSS file.
    """
    output = []
    d = feedparser.parse(filename)

    # Do some validity checks
    if d['feed']['subtitle'] != FEED_SUBTITLE:
        logger.error(f"Feed subtitle is not {FEED_SUBTITLE}")
        return output
    if d['feed']['author_detail']['email'] != FEED_AUTHOR_EMAIL:
        logger.error(f"Feed author is not {FEED_AUTHOR_EMAIL}")
        return output

    # Convert links list to dict indexed by 'rel'
    session_links = dict( (l['rel'], l) for l in d['feed']['links'] )
    if not session_links.get('self'):
        logger.error("No session information")
        return output
    session_href = session_links.get('self')['href']

    # Parse session_href URI to get period and meeting number
    # 'http://webtv.bundestag.de/player/macros/_v_q_2192_de/_s_podcast_skin/_x_s-144277506/bttv/podcast.xml?period=19&meetingNumber=4',
    session_info = parse_qs(urlparse(session_href).query)
    if not session_info.get('period'):
        logger.error("No period number")
        return output
    if not session_info.get('meetingNumber'):
        logger.error("No meeting number")
        return output
    period_number = int(session_info['period'][0])
    meeting_number = int(session_info['meetingNumber'][0])

    for e in d['entries']:
        links = dict( (l['rel'], l) for l in e ['links'] )

        if not 'enclosure' in links:
            # No media associated to the item.
            # FIXME: should we report the issue?
            logger.debug(f"No media associated to {filename}: {e['title']}")
            continue

        # we specify the input and the format...
        t = datetime.strptime(e['itunes_duration'],"%H:%M:%S")
        delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

        startdate = datetime(*e['published_parsed'][:6])
        enddate = startdate + delta

        item = {
            'ElectoralPeriodNumber': period_number,
            'SessionNumber': meeting_number,
            'AgendaItemTitle': e['title'],
            'VideoFileURI': links['enclosure']['href'],
            'MediaSourcePage': e['link'],
            'MediaDateStart': startdate.isoformat('T', 'seconds'),
            'MediaDateEnd': enddate.isoformat('T', 'seconds'),
            'MediaDuration': delta.total_seconds(),
            'MediaOriginID': os.path.basename(e['link']),
            'MediaCreator': e['author'],
            'SourceFilename': filename,
        }
        output.append(item)

    return output

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.warning(f"Syntax: {sys.argv[0]} file.xml ...")
        sys.exit(1)

    data = [ item for source in sys.argv[1:] for item in parse_rss(source) ]
    json.dump(data, sys.stdout, indent=2)
