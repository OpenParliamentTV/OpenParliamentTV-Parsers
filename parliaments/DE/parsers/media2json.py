#! /usr/bin/env python3

# Convert RSS media index file from http://webtv.bundestag.de into JSON with
# fields defined for OpenParliamentTV

import logging
logger = logging.getLogger(__name__)

from datetime import datetime, timedelta
import feedparser
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlparse, parse_qs

try:
    from parsers.common import fix_faction, fix_fullname
except ModuleNotFoundError:
    # Module not found. Tweak the sys.path
    base_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(base_dir))
    from parsers.common import fix_faction, fix_fullname

# Constants used for basic integrity checking: If these values are not
# present in the source data, then something must have changed and the
# parser should be checked anyway.
FEED_SUBTITLE = 'Deutscher Bundestag'
FEED_LICENSE = 'CC-BY-SA'
FEED_AUTHOR_EMAIL = 'mail@bundestag.de'
title_data_re = re.compile('Redebeitrag\s+von\s+(?P<fullname>.+?)\s+\((?P<faction>.+?)\)\s+am (?P<title_date>[\d.]+)\s+um\s+(?P<title_time>[\d:]+)\s+Uhr\s+\((?P<session_info>.+)\)')

def extract_title_data(title: str) -> dict:
    """Extract structured data from title string.

    Return a dict with fields if data could be extracted, else None.
    """
    # "Redebeitrag von Stephan Stracke (CDU/CSU) am 29.01.2010 um 14:05 Uhr (20. Sitzung, TOP ZP 2)"
    match = title_data_re.match(title)
    if match:
        return match.groupdict()
    else:
        return None

def fix_title(title: str) -> str:
    """Fix the titles to match with proceedings conventions
    """
    title = title.replace("TOP Sitzungsende", "Sitzungsende").replace("TOP Sitzungseröffnung", "Sitzungseröffnung")
    zusatz = re.findall('TOP(?:\s+\d+)?,?\s+ZP\s+(\d+)', title)
    if zusatz:
        return f"Zusatzpunkt {zusatz[0]}"
    title = re.sub('^TOP\s+(.+)', 'Tagesordnungspunkt \\1', title)
    return title

def parse_media_data(data) -> dict:
    """Parse a media-js structure

    It is a dict with
    {
    'root': root_feed_object,
    'entries': list_of_entries_to_parse
    }

    This generic structure is meant to accomodate single XML dumps of
    RSS feeds (in which case root.entries == entries) and the output
    of fetch_media script (which aggregates multiple pages of items
    into entries).
    """
    output = []
    root = data['root']
    entries = data['entries']

    # Do some validity checks
    if root['feed'].get('subtitle') != FEED_SUBTITLE:
        logger.error(f"Feed subtitle is not {FEED_SUBTITLE}: {root['feed'].get('subtitle')}")
        return output
    if root['feed']['author_detail'].get('email') != FEED_AUTHOR_EMAIL:
        logger.error(f"Feed author is not {FEED_AUTHOR_EMAIL}: {root['feed']['author_detail'].get('email')}")
        return output

    # Convert links list to dict indexed by 'rel'
    session_links = dict( (l['rel'], l) for l in root['feed']['links'] )
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

    for e in entries:
        links = dict( (l['rel'], l) for l in e ['links'] )

        if not 'enclosure' in links:
            # No media associated to the item.
            # FIXME: should we report the issue?
            logger.debug(f"No media associated: {e['title']}")
            continue

        # Use duration to compute end time
        t = datetime.strptime(e['itunes_duration'],"%H:%M:%S")
        delta = timedelta(hours=t.hour, minutes=t.minute, seconds=t.second)

        startdate = datetime(*e['published_parsed'][:6])
        enddate = startdate + delta
        mediaid = os.path.basename(e['link'])

        item = {
            "parliament": "DE",
            "electoralPeriod": {
                "number": period_number,
            },
            "session": {
                "number": meeting_number,
            },
            "agendaItem": {
                'title': e.get('subtitle'),
                'officialTitle': fix_title(e['title']),
            },
            "media": {
                'videoFileURI': links['enclosure']['href'],
                'sourcePage': e['link'],
                'duration': delta.total_seconds(),
                'creator': e['author'],

                # Note: commented fields are defined in
                # https://github.com/OpenParliamentTV/OpenParliamentTV-Platform/issues/2
                # but not available here

                #'audioFileURI': '' ,
                #"thumbnailURI": "https://example.com/thumb.png",
                #"thumbnailCreator": "Deutscher Bundestag",
                #"thumbnailLicense": "CC-BY-SA",
                "license": FEED_LICENSE,
                "originMediaID": mediaid,
                # "sourcePage": "https://dbtg.tv/fvid/7502148"
                # 'sourceFilename': filename,
            },
            'dateStart': startdate.isoformat('T', 'seconds'),
            'dateEnd': enddate.isoformat('T', 'seconds'),
        }
        if period_number >= 18:
            item['media']['audioFileURI'] = f"""https://static.p.core.cdn.streamfarm.net/1000153copo/ondemand/145293313/{mediaid}/{mediaid}_mp3_128kb_stereo_de_128.mp3"""

        metadata = extract_title_data(e['title'])
        if metadata is not None:
            # Faction may encode only faction, or role/faction information.
            # jq -r '.[] | .people[0].faction' data/examples/nmedia/*json | sort -u
            # in old dumps to get all different values.
            full_faction = metadata.get('faction', '')
            if '/' in full_faction:
                # Maybe it encodes a role
                role, faction = full_faction.split('/', 1)
                if role in ('CDU', 'B90', 'Bündnis 90'):
                    # Special cases for CDU and B90
                    faction = full_faction
                    role = None
            else:
                faction = full_faction
                role = None
            item['people'] = [
                {
                    'label': fix_fullname(metadata.get('fullname', '')),
                    'faction': fix_faction(faction),
                    'context': 'main-speaker',
                    'role': role
                }
            ]
            if metadata.get('session_info') is not None:
                # According to https://github.com/OpenParliamentTV/OpenParliamentTV-Parsers/issues/1
                # we should strip the Sitzung prefix from the session_info
                item['agendaItem']['officialTitle'] = fix_title(re.sub('^\d+\.\sSitzung,\s', '', metadata.get('session_info')))
            # FIXME: we have other fields: title_date, title_time that we could use for validation

        # Fix AgendaItemTitle if necessary
        if not item['agendaItem']['title']:
            title = fix_title(item['agendaItem']['officialTitle'])
            item['agendaItem']['title'] = title

        output.append(item)

    # Sort output by startDate - we have it here in ISO format so sorting is easy
    output.sort(key=lambda i: i['dateStart'])
    # Add explicit order field
    for i, item in enumerate(output):
        item['agendaItem']['speechIndex'] = i + 1
    return output

def parse_rss(filename: str) -> dict:
    """Parse a RSS file.
    """
    d = feedparser.parse(filename)

    return parse_media_data({ 'root': d,
                              'entries': d.entries })

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.warning(f"Syntax: {sys.argv[0]} file.xml ...")
        sys.exit(1)

    data = [ item for source in sys.argv[1:] for item in parse_rss(source) ]
    # Sort data according to dateStart
    data.sort(key=lambda m: m['dateStart'])
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
