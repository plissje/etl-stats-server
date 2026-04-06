import json
import os
from pathlib import Path

def load_aliases() -> dict[str, str]:
    """
    Load GUID aliases from aliases.json and return a flat mapping of:
    alias_guid (UPPER) -> master_guid (UPPER)
    """
    # Try multiple paths to find aliases.json
    paths = [
        Path("/app/data/aliases.json"),
        Path(os.getcwd()) / "data" / "aliases.json",
        Path(__file__).resolve().parent.parent / "aliases.json",
        Path(os.getcwd()) / "aliases.json"
    ]
    
    mapping_path = None
    for p in paths:
        if p.exists():
            mapping_path = p
            break
            
    if not mapping_path:
        return {}

    try:
        with open(mapping_path, "r") as f:
            data = json.load(f)
            flat_map = {}
            if isinstance(data, list):
                for entry in data:
                    master = str(entry.get("master_guid", "")).strip().upper()
                    if not master:
                        continue
                    aliases = entry.get("aliases", [])
                    if isinstance(aliases, list):
                        for a in aliases:
                            flat_map[str(a).strip().upper()] = master
            return flat_map
    except Exception as e:
        print(f"Warning: Failed to load aliases.json: {e}")
        return {}

def resolve_guid(guid: str) -> str:
    """Resolve a GUID to its master equivalent if defined in aliases.json."""
    if not guid:
        return guid
    mapping = load_aliases()
    g_upper = guid.strip().upper()
    return mapping.get(g_upper, g_upper)
