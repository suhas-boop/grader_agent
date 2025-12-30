
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.persistence import Persistence

try:
    print("Initializing Persistence...")
    db = Persistence()
    
    if not db.use_supabase:
        print("ERROR: Not using Supabase.")
        sys.exit(1)
        
    BAD_ID = "97d5f144-ffb5-44a0-b45a-8305593a4469"
    
    print(f"Deleting submission {BAD_ID}...")
    db.client.table("submissions").delete().eq("id", BAD_ID).execute()
    print("Deleted.")
    
except Exception as e:
    print(f"Error: {e}")
