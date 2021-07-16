# Methods common to parsing modules

def fix_fullname(label: str) -> str:
    if label is None:
        return label
    # Replace nb whitespace
    label = label.replace('\xa0', ' ')
    label = label.replace('Dr. ', '').replace('h. c. ', '').replace('Prof. ', '')
    return label

def fix_faction(label: str) -> str:
    if label is None:
        return label
    # Replace nb whitespace
    label = label.replace('\xa0', ' ')
    return label.replace('B90/Grüne', 'BÜNDNIS 90/DIE GRÜNEN')
