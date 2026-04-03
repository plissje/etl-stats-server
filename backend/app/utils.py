from datetime import datetime

# Memory-resident slow query log
SLOW_QUERIES = []

def record_slow_query(endpoint: str, duration: float, info: str = ""):
    if duration > 0.3:  # Threshold 300ms
        item = {
            "endpoint": endpoint,
            "duration": round(duration, 3),
            "info": info,
            "timestamp": datetime.utcnow().isoformat()
        }
        SLOW_QUERIES.append(item)
        # Keep only last 50
        while len(SLOW_QUERIES) > 50:
            SLOW_QUERIES.pop(0)
