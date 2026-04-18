import re

alias_list = [
    "Alpha.erNNNNNNNNN", "APATHEIDERANOAZZZZZZ", "Marker/ERANOAZZZ", "[DEL] ERANNNNNNNN",
    "Beta^e/2an", "^?EUROCUPEERANOAZZZZ", "BETA.ern", "North| ERANOAZZZZZZZZ", "Axis!ERANNNNNNNN",
    "beta.ernnnNNNNNNN", "gAmma! EaRannNoazzzz", "eRAnoooAzzz", "ALPHA.ERANTHEBRAVEE",
    "e/2annnnnnnn", "Alpha.erNNNNNNNNNNN", "Alpha.ERANnoAzzzzz", "ERaNNNNNNNNN",
    "ERANNNNNNNN", "KLA(+) ernnnnnnn", "gAmma! erNNNNNNNNNNN", "gAmma! eRnnnnnnnn",
    "BETA.ERANOAZZZ", "ALPHA.ERANOAZZZZZ", "NooAzzzzzzz", "ERANOOAZZZZZZZ", "noAzzzzzzz",
    "eranoazzzzzZz", "ERANOAZ", "noAzzzzzzzz", "B.ERANOAZZZZZXZZ", "ern", "Salem.ERANOAZZZ",
    "Adom! ERANNNNNNNN", "PRO4K.ERANOAZZZZZ"
]


def normalize_nick(nick: str) -> str:
    # Remove Quake colors
    nick = re.sub(r"\^[a-zA-Z0-9?]", "", nick)

    # Strip recognized gather tags (Axis, Allies, Alpha, Beta, Gamma, North, South, etc) 
    # Followed by typical separators (!, ., |, /)
    prefixes = r"^(alpha|beta|gamma|axis|allies|north|south|adom|salem|pro4k|marker|apatheid|eurocupe|kla\(\+\)|\[del\]|e/2|b)\s*[\.!\|/]?\s*"
    
    # Run multiple times in case of nested tags
    nick = re.sub(prefixes, "", nick, flags=re.IGNORECASE)
    
    # Strip any remaining standard tag brackets
    nick = re.sub(r"^\[.*?\]|^\{.*?\}|^\(.*?\) |^\<.*?\>", "", nick)
    
    # Remove leading non-alphabetic characters unless the name is entirely non-alphabetic
    alpha_nick = re.sub(r"^[^a-zA-Z0-9]+", "", nick)
    if alpha_nick:
        nick = alpha_nick

    return nick.strip()

for a in alias_list:
    print(f"{a:30} -> {normalize_nick(a)}")

