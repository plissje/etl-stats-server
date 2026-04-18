import re

alias_list = [
    "Alpha.erNNNNNNNNN", "APATHEIDERANOAZZZZZZ", "Marker/ERANOAZZZ", "[DEL] ERANNNNNNNN",
    "Beta^e/2an", "^?EUROCUPEERANOAZZZZ", "BETA.ern", "North| ERANOAZZZZZZZZ", "Axis!ERANNNNNNNN",
    "beta.ernnnNNNNNNN", "gAmma! EaRannNoazzzz", "eRAnoooAzzz", "ALPHA.ERANTHEBRAVEE",
    "e/2annnnnnnn", "Alpha.erNNNNNNNNNNN", "Alpha.ERANnoAzzzzz", "ERaNNNNNNNNN",
    "ERANNNNNNNN", "KLA(+) ernnnnnnn", "gAmma! erNNNNNNNNNNN", "gAmma! eRnnnnnnnn",
    "BETA.ERANOAZZZ", "ALPHA.ERANOAZZZZZ", "NooAzzzzzzz", "ERANOOAZZZZZZZ", "noAzzzzzzz",
    "eranoazzzzzZz", "ERANOAZ", "noAzzzzzzzz", "B.ERANOAZZZZZXZZ", "ern", "Salem.ERANOAZZZ",
    "Adom! ERANNNNNNNN", "PRO4K.ERANOAZZZZZ", "SomeTag] Nickname", "gg kostya", "lol|kostya"
]

def normalize_nick(nick: str) -> str:
    # 1. Strip quake colors
    n = re.sub(r"\^[a-zA-Z0-9?*]", "", nick)
    
    # 2. Strip common gather tags at start with space (Alpha , Beta , gg , lol )
    # This also helps with "gg kostya"
    n = re.sub(r'^(alpha|beta|gamma|axis|allies|north|south|adom|salem|pro4k|marker|apatheid|eurocupe|kla\(\+\)|\[del\]|e\/2|gg|lol|wow)\s+', '', n, flags=re.IGNORECASE)

    # 3. Split by common ET clan tag delimiters and take the trailing logical piece
    # Extended to include more delimiters
    parts = re.split(r'[!|.\/\]\}\>]\s*', n)
    for part in reversed(parts):
        p = part.strip()
        # Ensure it has letters/numbers and isn't just a tiny fragment
        if re.search(r'[a-zA-Z0-9]', p):
            return p
    return n.strip()

for a in alias_list:
    print(f"{a:30} -> {normalize_nick(a)}")

