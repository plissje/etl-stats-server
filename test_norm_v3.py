import re

alias_list = [
    "Alpha.erNNNNNNNNN", "APATHEIDERANOAZZZZZZ", "Marker/ERANOAZZZ", "[DEL] ERANNNNNNNN",
    "Beta^e/2an", "^?EUROCUPEERANOAZZZZ", "BETA.ern", "North| ERANOAZZZZZZZZ", "Axis!ERANNNNNNNN",
    "B.Und6rrr!!1", "N[e]o", "gg kostya", "lol|kostya"
]

def normalize_nick(nick: str) -> str:
    n = re.sub(r"\^[a-zA-Z0-9?*]", "", nick)
    
    # Strip common gather tags at start with space
    n = re.sub(
        r'^(alpha|beta|gamma|axis|allies|north|south|adom|salem|pro4k|marker|apatheid|eurocupe|kla\(\+\)|\[del\]|e\/2|gg|lol|wow)\s+', 
        '', 
        n, 
        flags=re.IGNORECASE
    )

    # Split by common ET clan tag delimiters
    parts = [p.strip() for p in re.split(r'[!|.\/\]\}\>]\s*', n) if p.strip()]
    if not parts:
        return n.strip()
        
    # Heuristic: Find the most significant part.
    # Usually the nick is the longest part or the last substantial one.
    # If the last part is very short (1-2 chars) and there's a longer part before it, 
    # it's likely a suffix (e.g. Name.1 or Name^7)
    
    # Default to the last part if it has letters
    best_part = parts[-1]
    
    # Look for a part that has letters and is longer than 2
    for p in reversed(parts):
        if re.search(r'[a-zA-Z]', p) and len(p) > 2:
            return p
            
    # Fallback to the last part that has anything
    for p in reversed(parts):
        if re.search(r'[a-zA-Z0-9]', p):
            return p

    return parts[-1]

for a in alias_list:
    print(f"{a:30} -> {normalize_nick(a)}")

