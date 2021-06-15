#! /usr/bin/env python3

# Extract transcript from data files from http://webtv.bundestag.de
# into JSON

import logging
logger = logging.getLogger(__name__)

from itertools import takewhile
import json
import re
import sys
from lxml import etree

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
    """Convert a list a list of <redner> to a dict of Person data indexed by identifier
    """
    result = {}
    for s in speakers:
        try:
            ident = s.attrib['id']
        except:
            import pdb; pdb.set_trace()

        if ident in result:
            # Already parsed
            continue
        firstname = s.findtext('.//vorname') or ""
        lastname = s.findtext('.//nachname') or ""
        fullname = f"{firstname} {lastname}"
        faction = s.findtext('.//fraktion') or ""
        # Persons can be without any party (independent) but join a faction. So we cannot assume any correspondence between both.
        #party = faction.split('/')[0]

        result[ident] = {
            'PersonFullName': fullname,
            'PersonFirstName': firstname,
            'PersonLastName': lastname,
            'PersonFaction': faction,
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
            # FIXME: Ignore for the moment
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
            elif klasse in ('J', 'J_1', 'O'):
                # Actual text. Output it with speaker information.
                yield {
                    'type': 'speech',
                    'speaker': speaker,
                    'speakerstatus': speakerstatus,
                    'text': c.text
                }
            # FIXME: all other <p> klasses are ignored for now

def parse_content(op, speaker, speakerstatus):
    """Parse an <tagesordnungspunkt> to output a structured sequence of tagged speech items.
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

    # An ordnungpunk normally consists of multiple <rede>.

    # But at the beginning there may be an introduction by the
    # president, in the form of multiple <p>. If this is the case,
    # produce a virtual <rede> called Introduction.

    # Consider only p or rede elements
    elements = [ node for node in op if node.tag == 'p' or node.tag == 'rede' ]

    # Produce a virtual introduction
    introduction = list(takewhile(lambda n: n.tag == 'p', elements))
    if introduction:
        speech = list(parse_speech(introduction, speaker, speakerstatus))
        yield {
            'type': 'text',
            'textBody': [
                {
                    'type': 'intro',
                    'text': "\n".join(s['text'] for s in speech),
                    'speaker': speech[0]['speaker']
                }
            ],
            'textDetails': speech
        }

    for el in elements:
        if el.tag != 'rede':
            # We just processed leading <p>. There may remain some
            # trailing <p>, which we ignore for now
            continue
        speech = list(parse_speech(el, speaker, speakerstatus))
        if speech:
            speaker = speech[-1]['speaker']
            speakerstatus = speech[-1]['speakerstatus']
            mainspeaker = next(filter(lambda s: s['speakerstatus'] == 'main speaker', speech), { 'speaker': 'Unknown' })['speaker']
            yield {
                'type': 'text',
                'textBody': [
                    {
                        'type': 'speech',
                        'text': "\n".join(s['text'] for s in speech if s['speakerstatus'] == 'main speaker'),
                        'speaker': mainspeaker
                    }
                ],
                'textDetails': speech
            }

def parse_documents(op):
    # FIXME
    return []

def parse_transcript(filename):
    # We are mapping 1 self-contained object/structure to each tagesordnungspunkt
    # This method is a generator that yields tagesordnungspunkt structures
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
            'timeStart': root.attrib.get('sitzung-start-uhrzeit', ''),
            'timeEnd': root.attrib.get('sitzung-ende-uhrzeit', ''),
        },
        'media': {
            'creator': metadata.findtext('.//herausgeber'),
        }
    }

    # Store dict for now because we will need the identifier for lookup
    # speakers = parse_speakers(root.findall('.//redner'))
    # data['speakers'] = list(speakers.values())

    speaker = "Unknown"
    speakerstatus = "Unknown"

    # Pass last speaker info from one speech to the next one
    for op in [ *root.findall('.//sitzungsbeginn'), *root.findall('.//tagesordnungspunkt') ]:
        speeches = list(parse_content(op, speaker, speakerstatus))
        if op.tag == 'sitzungsbeginn':
            title = 'Session introduction'
        else:
            title = op.attrib['top-id']
        speakers = list(parse_speakers(root.findall('.//redner')).values())
        if speeches:
            # Use last speech info to store last speaker
            speaker = speeches[-1]['textDetails'][-1]['speaker']
            speakerstatus = speeches[-1]['textDetails'][-1]['speakerstatus']
        yield {
            **session_metadata,
            'agendaItem': {
                "officialTitle": title,
                # FIXME: we use the same for the moment. Not sure if it can be extracted (.T_fett is not correct)
                "title": title,
            },
            'speeches': speeches,
            'people': speakers,
            'documents': list(parse_documents(op)),
        }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        logger.warning(f"Syntax: {sys.argv[0]} file.xml ...")
        sys.exit(1)

    data = list(parse_transcript(sys.argv[1]))
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
