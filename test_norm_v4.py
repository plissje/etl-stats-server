import re

def strip_quake_colors(name):
    if not name: return ""
    return re.sub(r"\^[a-zA-Z0-9?*]", "", name)

def normalize_nick(nick: str) -> str:
    if not nick:
        return ""
    
    # 1. Strip quake colors
    n = strip_quake_colors(nick)
    
    # 2. Strip common gather tags at start with space (Alpha , Beta , gg , lol )
    n = re.sub(
        r'^(alpha|beta|gamma|axis|allies|north|south|adom|salem|pro4k|marker|apatheid|eurocupe|kla\(\+\)|\[del\]|e\/2|gg|lol|wow)\s+', 
        '', 
        n, 
        flags=re.IGNORECASE
    )

    # 3. Split by common ET clan tag delimiters
    # Example: "B.Und6rrr!!1" -> ["B", "Und6rrr", "1"]
    parts = [p.strip() for p in re.split(r'[!|.\/\]\}\>]\s*', n) if p.strip()]
    if not parts:
        return n.strip()
        
    # Heuristic: Find the most significant part.
    # We prefer the first part that has letters and is longer than 2 characters (e.g. the main nick)
    # searching from the end.
    for p in reversed(parts):
        if re.search(r'[a-zA-Z]', p) and len(p) > 2:
            return p
            
    # Fallback: Last part that contains any alphanumeric characters
    for p in reversed(parts):
        if re.search(r'[a-zA-Z0-9]', p):
            return p
            
    return parts[-1]

test_cases = [
    ('BETA.KreEp', '^mBETA^0.^7KreEp'),
    ('[parodia] Add3X', '^j[parodia] ^7Add3X'),
    ('gAmma! AnT', '^ngAmma^0! ^7AnT')
]

for display, raw in test_cases:
    norm = normalize_nick(raw)
    print(f"RAW: {raw:20} -> NORM: {norm:15} (Match: {norm == display})")
