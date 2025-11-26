import os
import json
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "requests.jsonl")

os.makedirs(LOGS_DIR, exist_ok=True)

def log_request(data: dict):
    """
    Appends a JSON record to logs/requests.jsonl
    """
    try:
        # Ensure timestamp exists
        if "timestamp" not in data:
            data["timestamp"] = time.time()
            
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
    except Exception as e:
        print(f"Telemetry logging failed: {e}")