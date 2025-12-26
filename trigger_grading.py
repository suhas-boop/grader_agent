
import os
import sys

sys.path.append(os.getcwd())

from src.persistence import Persistence
import requests

db = Persistence()
subs = db.get_all()

if not subs:
    print("No submissions found.")
else:
    # Find latest
    latest = sorted(subs, key=lambda s: s.upload_time, reverse=True)[0]
    print(f"Triggering grading for {latest.id} ({latest.filename})...")
    
    # We can call the process endpoint
    url = f"http://127.0.0.1:8000/api/submissions/{latest.id}/process"
    try:
        res = requests.post(url)
        print(f"Response: {res.status_code} {res.text}")
    except Exception as e:
        print(f"Error calling API: {e}")
