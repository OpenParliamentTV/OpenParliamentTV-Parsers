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
    # Strip leading/trailing : - .
    label = label.strip(':').strip('–').strip('.')
    # Fix strange notation, like in 19040, 19170, 19176...
    label = label.replace('räsident in', 'räsidentin')
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
    # Replace non-breaking whitespaces (\xa0) and multiple whitespaces
    label = re.sub(r'\s+', ' ', label)
    return label.replace('B90/Grüne', 'BÜNDNIS 90/DIE GRÜNEN')

def fix_role(role: str) -> str:
    """Return a standardized role if defined.

    Else return the unchanged role.
    """
    return STATUS_TRANSLATION.get(role, role)
