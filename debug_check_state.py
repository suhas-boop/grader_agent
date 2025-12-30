
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.persistence import Persistence, SubmissionMetadata

try:
    print("Initializing Persistence...")
    db = Persistence()
    
    if not db.use_supabase:
        print("ERROR: Not using Supabase. Check env vars.")
        sys.exit(1)
        
    print(f"Connected to Supabase: {db.supabase_url}")
    
    # List DB Submissions
    print("\n--- DB Submissions ---")
    subs = db.get_all()
    for s in subs:
        print(f"ID: {s.id} | File: {s.filename} | Status: {s.status}")
        
    # List Storage Files
    print("\n--- Storage Files (bucket: uploads) ---")
    try:
        files = db.client.storage.from_("uploads").list()
        # storage.list return type might vary, let's inspect
        for f in files:
            print(f"File: {f['name']} | Size: {f['metadata']['size']}")
    except Exception as e:
        print(f"Error listing files: {e}")

except Exception as e:
    print(f"General Error: {e}")
    import traceback
    traceback.print_exc()
