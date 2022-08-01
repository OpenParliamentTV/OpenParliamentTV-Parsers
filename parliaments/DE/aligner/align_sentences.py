#! /usr/bin/env python3

"""Time-align sentences from a list of speeches
"""

import logging
logger = logging.getLogger(__name__)

import argparse
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
DEFAULT_CACHEDIR = '/tmp/cache'

def sentence_iter(speech: dict) -> iter:
    """Iterate over all sentences in a speech, adding a unique identifier.
    """
    speechIndex = speech['agendaItem']['speechIndex']
    for contentIndex, content in enumerate(speech.get('textContents', [])):
        for bodyIndex, body in enumerate(content['textBody']):
            for sentenceIndex, sentence in enumerate(content['textBody']):
                ident = f"s{speechIndex}-{contentIndex}-{bodyIndex}-{sentenceIndex}"
                yield ident, sentence

def cachedfile(speech: dict, extension: str, cachedir: Path = None) -> Path:
    """Return a filename with given extension
    """
    filename = f"{speech['session']['number']}{speech['agendaItem']['speechIndex']}.{extension}"
    if not cachedir.is_dir():
        cachedir.mkdir()
    return cachedir / filename

def audiofile(speech: dict, cachedir: Path = None) -> Path:
    """Get an audiofile for the given dict.

    Either it is already cached (return filename) or download it
    first.

    If anything wrong happens, return None
    """
    audio = cachedfile(speech, 'mp3', cachedir)
    if not audio.exists():
        # Check that we have enough disk space for caching
        total, used, free = shutil.disk_usage(cachedir)
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


def align_audio(source: list, language: str, cachedir: Path = None) -> list:
    """Align list of speeches to add timing information to sentences.

    The structure is modified in place, and returned.
    """
    if cachedir is None:
        cachedir = Path(DEFAULT_CACHEDIR)
        logger.warning(f"No cache dir specified - using default {cachedir}")
    else:
        cachedir = Path(cachedir)

    for speech in source:
        # Do we have proceedings data?
        text_data = [ "|".join((ident, sentence['text'])) + os.linesep
                      for ident, sentence in sentence_iter(speech) ]
        if len(text_data) == 0:
            logger.warning(f"No text data to align - skipping {speech['session']['number']}{speech['agendaItem']['speechIndex']}")
            continue

        # Download audio file
        audio = audiofile(speech, cachedir)
        if audio is None:
            continue

        # Generate parsed text format file with identifier + sentence
        sentence_file = cachedfile(speech, 'txt', cachedir)
        with open(sentence_file, 'wt') as sf:
            sf.writelines(text_data)

        logger.warning(f"Aligning {sentence_file} with {audio}")
        # Do the alignment
        task = Task(config_string=f"""task_language={language}|is_text_type=parsed|os_task_file_format=json""")
        task.audio_file_path_absolute = str(audio.absolute())
        task.text_file_path_absolute = str(sentence_file.absolute())
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

        # Cleanup generated files (keep cached audio)
        sentence_file.unlink()

    return source

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Time-align speech sentences.")
    parser.add_argument("source", metavar="source", type=str, nargs='?',
                        help="Source file (merged format)")
    parser.add_argument("destination", metavar="destination", type=str, nargs='?',
                        help="Destination file")
    parser.add_argument("--lang", type=str, default="deu",
                        help="Language")
    parser.add_argument("--cache-dir", type=str, default=None,
                        help="Cache directory")

    args = parser.parse_args()
    if args.source is None:
        parser.print_help()
        sys.exit(1)

    with open(args.source) as f:
        source = json.load(f)
    output = align_audio(source, args.lang, args.cache_dir)
    with (open(args.destination, 'w') if args.destination else sys.stdout) as f:
        json.dump(output, f)
