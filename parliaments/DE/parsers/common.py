# Methods common to parsing modules
import logging
logger = logging.getLogger(__name__)

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

    # Strip leading/trailing non-alphabetic chars
    label = re.sub('^[^\w]+', '', label)
    label = re.sub('[^\w]+$', '', label)
    # Replace non-breaking whitespaces
    label = re.sub(r'\xc2\xa0', ' ', label)
    # Replace multiple whitespaces
    label = re.sub(r'\s+', ' ', label)
    # Fix strange notation, like in 19040, 19170, 19176...
    label = label.replace('räsident in', 'räsidentin')

    # Split at the first whitespace to get possible status information
    info = re.split('\s+', label, 1)
    if len(info) == 2 and info[0] in STATUS_TRANSLATION:
        return (fix_fullname(info[1]), STATUS_TRANSLATION.get(info[0]))

    # No matching key. Assume that there is no status at the beginning.
    return (fix_fullname(label), None)

def fix_fullname(label: str) -> str:
    if label is None:
        return label
    # Replace non-breaking whitespaces
    label = re.sub(r'\xc2\xa0', ' ', label)
    # Replace multiple whitespaces
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

def fixup_execute(fix: dict, entry: dict) -> dict:
    """Execute a fixup action on entry.

    The action may transform things in place.
    Return the transformed entry.
    """
    if fix['action'] == 'replace':
        value = entry.get(fix['field'])
        if value is None:
            logger.debug(f"No value for field {fix['field']} in fixup action")
            return entry
        new_value = re.sub(fix['from'], fix['to'], value)
        if new_value != value:
            entry[f"{fix['field']}-original"] = value
            entry[fix['field']] = new_value
    else:
        logger.error(f"Unknown action {fix['action']}")
    return entry
