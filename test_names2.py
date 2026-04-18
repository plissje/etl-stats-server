import re

alias_list = [
    "Alpha.erNNNNNNNNN", "APATHEIDERANOAZZZZZZ", "Marker/ERANOAZZZ", "[DEL] ERANNNNNNNN",
    "Beta^e/2an", "^?EUROCUPEERANOAZZZZ", "BETA.ern", "North| ERANOAZZZZZZZZ", "Axis!ERANNNNNNNN",
    "beta.ernnnNNNNNNN", "gAmma! EaRannNoazzzz", "eRAnoooAzzz", "ALPHA.ERANTHEBRAVEE",
    "e/2annnnnnnn", "Alpha.erNNNNNNNNNNN", "Alpha.ERANnoAzzzzz", "ERaNNNNNNNNN",
    "ERANNNNNNNN", "KLA(+) ernnnnnnn", "gAmma! erNNNNNNNNNNN", "gAmma! eRnnnnnnnn",
    "BETA.ERANOAZZZ", "ALPHA.ERANOAZZZZZ", "NooAzzzzzzz", "ERANOOAZZZZZZZ", "noAzzzzzzz",
    "eranoazzzzzZz", "ERANOAZ", "noAzzzzzzzz", "B.ERANOAZZZZZXZZ", "ern", "Salem.ERANOAZZZ",
    "Adom! ERANNNNNNNN", "PRO4K.ERANOAZZZZZ", "SomeTag]  Nickname"
]

def normalize_nick(nick: str) -> str:
    # 1. Strip quake colors
    nick = re.sub(r"\^[a-zA-Z0-9?*]", "", nick)
    
    # 2. Split by common clan tag delimiters
    parts = re.split(r'[!|.\/\]\}\>]\s*', nick)
    
    # 3. Take the last part that has letters in it, else just return the original stripped output
    for part in reversed(parts):
        part = part.strip()
        if re.search(r'[a-zA-Z]', part):
            return part
            
    # Fallback if no letters were found in any segment
    return nick

for a in alias_list:
    print(f"{a:30} -> {normalize_nick(a)}")

