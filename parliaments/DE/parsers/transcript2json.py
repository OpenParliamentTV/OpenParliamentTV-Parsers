#! /usr/bin/env python3

# Extract transcript from data files from http://webtv.bundestag.de
# into JSON

# It output an array of items, each items represents a speech (rede) with additionnal metadata


import logging
logger = logging.getLogger(__name__)

from itertools import takewhile
import json
import re
import sys
from lxml import etree

PROCEEDINGS_LICENSE = "Public Domain"
PROCEEDINGS_LANGUAGE = "DE-de"

STATUS_TRANSLATION = {
    'Präsident': 'president',
    'Präsidentin': 'president',
    'Vizepräsident': 'vice-president',
    'Vizepräsidentin': 'vice-president',
    'Alterspräsident': 'co-president',
    'Alterspräsidentin': 'co-president',
}

ddmmyyyy_re = re.compile('(?P<dd>\d\d)\.(?P<mm>\d\d)\.(?P<yyyy>\d\d\d\d)')

def parse_speakers(speakers):
    """Convert a list a list of <redner> to a dict of Person data indexed by fullname
    """
    result = {}
    for s in speakers:
        ident = s.attrib['id']
        if ident in result:
            # Already parsed
            continue
        firstname = s.findtext('.//vorname') or ""
        lastname = s.findtext('.//nachname') or ""
        fullname = f"{firstname} {lastname}"
        faction = s.findtext('.//fraktion') or ""
        # Persons can be without any party (independent) but join a faction. So we cannot assume any correspondence between both.
        #party = faction.split('/')[0]

        result[fullname] = {
            'fullname': fullname,
            'firstname': firstname,
            'lastname': lastname,
            'faction': faction,
            'identifier': ident
        }
    return result

def parse_speech(elements, speaker, speakerstatus):
    # speaker/speakerstatus are initialized from the calling method
    # speakerstatus: president / vice-president / main speaker / speaker
    for c in elements:
        if c.tag == 'name':
            # Pr/VP name, strip trailing :
            speaker = c.text.strip(':')
            if (speaker.startswith('Präsident')
                or speaker.startswith('Vizepräsident')
                or speaker.startswith('Alterspräsident')):
                status, speaker = speaker.split(' ', 1)
                speakerstatus = STATUS_TRANSLATION.get(status, status)
            continue
        if c.tag == 'kommentar':
            yield {
                    'type': 'comment',
                    'speaker': None,
                    'speakerstatus': None,
                    'text': c.text
                }
            continue
        if c.tag == 'p':
            klasse = c.attrib.get('klasse')
            if klasse == 'redner':
                # Speaker identification
                firstname = c.findtext('.//vorname') or ""
                lastname = c.findtext('.//nachname') or ""
                speaker = f"{firstname} {lastname}"
                speakerstatus = 'main speaker'
                continue
            elif klasse == 'N':
                # Speaker name - Präsident or Vizepräsident
                speaker = c.text.strip(':')
                if (speaker.startswith('Präsident')
                    or speaker.startswith('Vizepräsident')
                    or speaker.startswith('Alterspräsident')):
                    status, speaker = speaker.split(' ', 1)
                    speakerstatus = STATUS_TRANSLATION.get(status, status)
                continue
            elif klasse in ('J', 'J_1', 'O') and c.text:
                # Actual text. Output it with speaker information.
                yield {
                    'type': 'speech',
                    'speaker': speaker,
                    'speakerstatus': speakerstatus,
                    'text': c.text
                }
            # FIXME: all other <p> klasses are ignored for now

def parse_ordnungpunkt(op, speaker, speakerstatus):
    """Parse an <tagesordnungspunkt> to output a sequence of tagged speech items.

    It is a generator that generates 1 array of speech items by rede.

    Each tagesordnungspunkt has a number of speeches (rede), each having a main speaker (redner)

    Speaker names can be specified in multiple ways:
    - either <p klasse="redner"> which contains the full redner identification
    - or <p klasse="N"> which contains a name (mostly for Präsident)
    - or a <name> tag (mostly for Präsident)
    - or sometimes in freeform in <kommentar> like "(Steffi Lemke [BÜNDNIS 90/DIE GRÜNEN]: Da freut sich die FDP auch drüber!)" (ignored for now)

    so we have to go through items in order and maintain a "speaker" state variable.

    On top of that, op may contain <rede> or <p> children (and <rede> contains <p>)
    """

    # import IPython; IPython.embed()

    # An ordnungpunkt normally consists of multiple <rede>.

    # But at the beginning there may be an introduction by the
    # president, in the form of multiple <p>. If this is the case,
    # produce a virtual <rede> called Introduction.

    # Consider only p or rede elements
    elements = [ node for node in op if node.tag in ('p', 'name', 'rede') ]

    # Produce a virtual introduction
    introduction = list(takewhile(lambda n: n.tag in ('p', 'name'), elements))
    if introduction:
        turns = list(parse_speech(introduction, speaker, speakerstatus))
        if turns:
            speaker = turns[0]['speaker']
            speakerstatus = turns[0]['speakerstatus']
            yield turns

    for el in elements:
        if el.tag != 'rede':
            # We just processed leading <p>. There may remain some
            # trailing <p>, which we ignore for now
            continue
        turns = list(parse_speech(el, speaker, speakerstatus))
        if turns:
            speaker = turns[-1]['speaker']
            speakerstatus = turns[-1]['speakerstatus']
            # mainspeaker = next(filter(lambda s: s['speakerstatus'] == 'main speaker', speech), { 'speaker': 'Unknown' })['speaker']
            yield turns

    # FIXME: process trailing <p>?

def parse_documents(op):
    for doc in op.findall('p[@klasse="T_Drs"]'):
        # There may be multiple Drucksache in a single .T_Drs:
        # "Drucksachen 19/27871, 19/27822, 19/27315, 19/29694"
        for session, ref in re.findall('(\d\d)/(\d+)', doc.text):
            padded = ref.rjust(5, '0')
            yield {
                "type": "officialDocument",
                "label": f"Drucksache {session}/{ref}",
                "sourceURI": f"https://dserver.bundestag.de/btd/{session}/{padded[:3]}/{session}{padded}.pdf"
            }


def parse_transcript(filename, sourceUri=None):
    # We are mapping 1 self-contained object/structure to each tagesordnungspunkt
    # This method is a generator that yields tagesordnungspunkt structures
    if sourceUri is None:
        sourceUri = filename
    tree = etree.parse(filename)
    root = tree.getroot()

    intro = root.find('vorspann')
    metadata = intro.find('kopfdaten')

    date = root.attrib.get('sitzung-datum', '')
    if date:
        # Convert from MM.DD.YYYY to ISO format YYYY-MM-DD
        match = ddmmyyyy_re.match(date)
        if match:
            d = match.groupdict()
            date = f"""{d['yyyy']}-{d['mm']}-{d['dd']}"""

    # metadata common to all tagesordnungspunkt
    session_metadata = {
        'electoralPeriod': {
            'number': metadata.findtext('.//wahlperiode'),
        },
        'session': {
            'number': metadata.findtext('.//sitzungsnr'),
            'date': date,
            # FIXME: convert to dateStart / dateEnd taking into account the possible day change
            'timeStart': root.attrib.get('sitzung-start-uhrzeit', ''),
            'timeEnd': root.attrib.get('sitzung-ende-uhrzeit', ''),
        },
    }

    # Store speaker dict
    speaker_info = parse_speakers(root.findall('.//redner'))

    speaker = "Unknown"
    speakerstatus = "Unknown"

    # Pass last speaker info from one speech to the next one
    for op in [ *root.findall('.//sitzungsbeginn'),
                *root.findall('.//tagesordnungspunkt'),
                *root.findall('.//sitzungsende') ]:
        speeches = list(parse_ordnungpunkt(op, speaker, speakerstatus))
        if op.tag == 'sitzungsbeginn':
            title = 'Sitzungsbeginn'
        elif op.tag == 'sitzungsende':
            title = 'Sitzungsende'
        else:
            title = op.attrib['top-id']


        if speeches:
            # Use last turn from last speech info to get last speaker
            speaker = speeches[-1][-1]['speaker']
            speakerstatus = speeches[-1][-1]['speakerstatus']

        documents = list(parse_documents(op))

        # Yield 1 structure per speech
        for speech in speeches:
            # Extract list of speakers for this speech
            speakerstatus = dict( (turn['speaker'], turn['speakerstatus'])
                                  for turn in speech
                                  # Do not consider null speakers (for comments)
                                  if turn['speaker'] )
            def speaker_item(fullname, status):
                info = speaker_info.get(fullname)
                if info:
                    return {
                        "type": "memberOfParliament",
                        "label": fullname,
                        "firstname": info['firstname'],
                        "lastname": info['lastname'],
                        "context": status,
                        "faction": info['faction'],
                    }
                else:
                    return {
                        "type": "memberOfParliament",
                        "label": fullname,
                        "context": status
                    }
            speakers = [ speaker_item(fullname, status)
                         for fullname, status in speakerstatus.items() ]

            yield {
                **session_metadata,
                'agendaItem': {
                    "officialTitle": title,
                    # The human-readable title is not present in proceedings, it will be in media
                    # "title": title,
                },
                'textContents': [
                    {
                        "type": "proceedings",
                        "textBody": speech,
                        "sourceURI": sourceUri,
                        "creator": metadata.findtext('.//herausgeber'),
                        "license": PROCEEDINGS_LICENSE,
                        "language": PROCEEDINGS_LANGUAGE,
                        "originTextID": root.attrib.get('issn', '')
                    }
                ],
                'people': speakers,
                'documents': documents,
            }

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.warning(f"Syntax: {sys.argv[0]} file.xml [Source URI]")
        sys.exit(1)

    data = list(parse_transcript(sys.argv[1]))
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
