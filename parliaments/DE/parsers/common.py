# Methods common to parsing modules

import re

STATUS_TRANSLATION = {
    'Präsident': 'president',
    'Präsidentin': 'president',
    'Vizepräsident': 'vice-president',
    'Vizepräsidentin': 'vice-president',
    'Alterspräsident': 'interim-president',
    'Alterspräsidentin': 'interim-president',
}

def parse_fullname(label: str) -> tuple:
    """Return a tuple (name, status)

    status will most often be None, except if the label starts with Prasident (or variants)
    """
    if label is None:
        return None
    # Strip leading/trailing :
    label = label.strip(':').strip('–')
    first, rest = re.split('\s+', label, 1)
    if first in STATUS_TRANSLATION:
        return (fix_fullname(rest), STATUS_TRANSLATION.get(first))
    # No matching key. Assume that there is no status at the beginning.
    return (fix_fullname(label), None)

def fix_fullname(label: str) -> str:
    if label is None:
        return label
    # Replace non-breaking whitespaces (\xa0) and multiple whitespaces
    label = re.sub(r'\s+', ' ', label)
    label = label.replace('Dr. ', '').replace('h. c. ', '').replace('Prof. ', '').replace('Graf Graf ', 'Graf ')
    return label

def fix_faction(label: str) -> str:
    if label is None:
        return label
    # Replace nb whitespace
    label = label.replace('\xa0', ' ')
    return label.replace('B90/Grüne', 'BÜNDNIS 90/DIE GRÜNEN')
