import re

_COLOR = re.compile(r"\^[0-9]")


def strip_quake_colors(name: str) -> str:
    if not name:
        return ""
    return _COLOR.sub("", name)
