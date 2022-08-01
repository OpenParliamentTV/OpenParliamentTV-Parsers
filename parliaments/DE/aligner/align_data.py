#! /usr/bin/env python3

import logging
logger = logging.getLogger(__name__)

import json
import os
from pathlib import Path
import shutil
import sys
from urllib.request import urlretrieve

from aeneas.executetask import ExecuteTask
from aeneas.task import Task

# We want to check that we have 1GB minimum available cache size
MIN_CACHE_SPACE = 1024 * 1024 * 1024

AUDIOCACHEDIR = Path('/tmp/cached')
if not AUDIOCACHEDIR.is_dir():
    AUDIOCACHEDIR.mkdir()

def sentence_iter(speech: dict) -> iter:
    """Iterate over all sentence in a speech, adding an identifier.
    """
    speechIndex = speech['agendaItem']['speechIndex']
    for contentIndex, content in enumerate(speech.get('textContents', [])):
        for bodyIndex, body in enumerate(content['textBody']):
            for sentenceIndex, sentence in enumerate(content['textBody']):
                ident = f"s{speechIndex}-{contentIndex}-{bodyIndex}-{sentenceIndex}"
                yield ident, sentence

def cachedfile(speech: dict, extension: str) -> Path:
    filename = f"{speech['session']['number']}{speech['agendaItem']['speechIndex']}.{extension}"
    return AUDIOCACHEDIR / filename

def audiofile(speech: dict) -> Path:
    """Get an audiofile for the given dict.

    Either it is already cached (return filename) or download it
    first.

    If anything wrong happens, return None
    """
    audio = cachedfile(speech, 'mp3')
    if not audio.exists():
        # Check that we have enough disk space for caching
        total, used, free = shutil.disk_usage(AUDIOCACHEDIR)
        if free < MIN_CACHE_SPACE:
            logger.error(f"No enough disk space for cache dir: {free / 1024 / 1024 / 1024} GB")
            return None

        # Not yet cached file - download it
        audioURI = speech.get('media', {}).get('audioFileURI')
        if not audioURI:
            logger.error(f"No audioFileURI for {speech['session']['number']}{speech['agendaItem']['speechIndex']}")
            return None
        logger.warning(f"Downloading {audioURI} into {audio.name}")
        try:
            (fname, headers) = urlretrieve(audioURI, str(audio))
        except Exception as e:
            logger.error(f"Cannot download {audioURI}: {e}")
            return None
    return audio


def align_audio(source: list) -> list:
    """Align list of speeches to add timing information to sentences.

    The structure is modified in place, and returned.
    """
    for speech in source:
        # Download audio file
        audio = audiofile(speech)
        if audio is None:
            continue

        # Generate parsed text format file with identifier + sentence
        sentence_file = cachedfile(speech, 'txt')
        with open(sentence_file, 'wt') as sf:
            for ident, sentence in sentence_iter(speech):
                sf.write("|".join( (ident, sentence['text'])) + os.linesep)

        # Do the alignment
        task = Task(config_string="""task_language=deu|task_language=eng|is_text_type=parsed|os_task_file_format=json""")
        task.audio_file_path_absolute = str(audio)
        task.text_file_path_absolute = str(sentence_file)
        # process Task
        ExecuteTask(task).execute()

        # Keep only REGULAR fragments (other can be HEAD/TAIL...)
        fragments = dict(  (f.identifier, f)
                           for f in task.sync_map_leaves()
                           if f.is_regular )

        # |task_adjust_boundary_no_zero=false|task_adjust_boundary_nonspeech_min=2|task_adjust_boundary_nonspeech_string=REMOVE|task_adjust_boundary_nonspeech_remove=REMOVE|is_audio_file_detect_head_min=0.1|is_audio_file_detect_head_max=3|is_audio_file_detect_tail_min=0.1|is_audio_file_detect_tail_max=3|task_adjust_boundary_algorithm=aftercurrent|task_adjust_boundary_aftercurrent_value=0.5|is_audio_file_head_length=1" '.$secureOutputPath.' 2>&1';

        # Inject timing information back into the source data
        for ident, sentence in sentence_iter(speech):
            sentence['timeStart'] = str(fragments[ident].begin)
            sentence['timeEnd'] = str(fragments[ident].end)

    return source

if __name__ == '__main__':
    merged_source = sys.argv[1]
    merged_dest = sys.argv[2]

    with open(merged_source) as f:
        source = json.load(f)
    output = align_audio(source)
    with open(merged_dest, 'w') as f:
        json.dump(output, f)
