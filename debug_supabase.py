
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

from src.persistence import Persistence

try:
    print("Initializing Persistence...")
    db = Persistence()
    
    if not db.use_supabase:
        print("ERROR: Not using Supabase. Check env vars or hardcoded values.")
        sys.exit(1)
        
    print("Supabase Configured.")
    print(f"URL: {db.supabase_url}")
    
    # Try to list buckets (if possible with this client wrapper, but standard client has storage.list_buckets()?)
    # Actually, let's just try the save_file which is failing.
    
    print("Attempting to save a test file...")
    import uuid
    unique_name = f"debug_test_{uuid.uuid4()}.txt"
    try:
        res = db.save_file(b"test content", unique_name)
        print(f"SUCCESS: Saved file at {res}")
        
        # Now test add_submission
        print("Attempting to add submission...")
        from src.persistence import SubmissionMetadata
        from datetime import datetime
        
        meta = SubmissionMetadata(
            id=str(uuid.uuid4()),
            filename=unique_name,
            upload_time=datetime.now().isoformat(),
            assignment_type="essay",
            student_id="debug_user",
            score=10.0, # This field was causing issues
            feedback_summary="Test feedback" # This one too
        )
        
        db.add_submission(meta)
        print("SUCCESS: Added submission execution completed.")
        
    except Exception as e:
        print("FAILURE: Operation raised exception:")
        print(e)
        import traceback
        traceback.print_exc()


except Exception as e:
    print(f"General Error: {e}")
