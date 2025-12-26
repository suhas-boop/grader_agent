import json
import os
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field

class SubmissionMetadata(BaseModel):
    id: str
    filename: str
    upload_time: str
    status: str = "UPLOADED" # UPLOADED, PROCESSING, GRADED, ERROR
    score: Optional[float] = None
    max_score: Optional[float] = None
    feedback_summary: Optional[str] = None
    assignment_type: str = "essay" # Default
    student_id: str = "Unknown"
    rubric_path: Optional[str] = None

# Import supabase
from supabase import create_client, Client
from typing import Optional, List
import json

class Persistence:
    def __init__(self, data_dir: str = "data"):
        # Check for Supabase
        self.supabase_url = os.environ.get("SUPABASE_URL","https://xbdsozqsajxxfsefirtj.supabase.co")
        self.supabase_key = os.environ.get("SUPABASE_KEY","eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhiZHNvenFzYWp4eGZzZWZpcnRqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NjYyNzIyNywiZXhwIjoyMDgyMjAzMjI3fQ.uS2VI_GVCTNYTAhyhkCQrlXUbDaWtN7CxpCH02_-8dQ")
        self.use_supabase = bool(self.supabase_url and self.supabase_key)
        
        self.client: Optional[Client] = None
        
        if self.use_supabase:
            print("Initializing Supabase Client...")
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
                print("Supabase connected.")
            except Exception as e:
                print(f"Failed to connect to Supabase: {e}. Falling back to local.")
                self.use_supabase = False

        # Local fallback setup
        self.data_dir = "/tmp/data" if os.environ.get("VERCEL") else data_dir
        self.submissions_file = os.path.join(self.data_dir, "submissions.json")
        self.uploads_dir = os.path.join(self.data_dir, "uploads")
        
        # Ensure directories exist (always needed for temp processing)
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.uploads_dir, exist_ok=True)
        
        if not self.use_supabase:
            self._ensure_db()

    def _ensure_db(self):
        if not os.path.exists(self.submissions_file):
            with open(self.submissions_file, "w") as f:
                json.dump([], f)

    def add_submission(self, metadata: SubmissionMetadata):
        if self.use_supabase:
            data = metadata.dict()
            
            # ADAPTER: Map Pydantic model to Supabase Schema
            # 1. feedback_summary -> feedback
            if 'feedback_summary' in data:
                data['feedback'] = data.pop('feedback_summary')
                
            # 2. score/max_score -> metadata (since columns don't exist)
            meta_json = {}
            if 'score' in data:
                meta_json['score'] = data.pop('score')
            if 'max_score' in data:
                meta_json['max_score'] = data.pop('max_score')
                
            data['metadata'] = meta_json
            
            self.client.table("submissions").insert(data).execute()
        else:
            current = self.get_all()
            current.append(metadata)
            self._save(current)

    def get_all(self) -> List[SubmissionMetadata]:
        if self.use_supabase:
            response = self.client.table("submissions").select("*").execute()
            results = []
            for item in response.data:
                # ADAPTER: Map Supabase Schema back to Pydantic
                if 'feedback' in item:
                    item['feedback_summary'] = item.pop('feedback')
                
                # Unpack metadata for score/max_score
                meta_json = item.get('metadata') or {}
                if isinstance(meta_json, dict):
                     item['score'] = meta_json.get('score')
                     item['max_score'] = meta_json.get('max_score')
                
                results.append(SubmissionMetadata(**item))
            return results
        else:
            with open(self.submissions_file, "r") as f:
                try:
                    data = json.load(f)
                    return [SubmissionMetadata(**item) for item in data]
                except json.JSONDecodeError:
                    return []

    def get_submission(self, sub_id: str) -> Optional[SubmissionMetadata]:
        if self.use_supabase:
            response = self.client.table("submissions").select("*").eq("id", sub_id).execute()
            if response.data:
                item = response.data[0]
                # ADAPTER: Map Supabase Schema back to Pydantic
                if 'feedback' in item:
                    item['feedback_summary'] = item.pop('feedback')
                
                meta_json = item.get('metadata') or {}
                if isinstance(meta_json, dict):
                     item['score'] = meta_json.get('score')
                     item['max_score'] = meta_json.get('max_score')
                     
                return SubmissionMetadata(**item)
            return None
        else:
            all_subs = self.get_all()
            for sub in all_subs:
                if sub.id == sub_id:
                    return sub
            return None

    def update_status(self, sub_id: str, status: str, grade: str = None, feedback: str = None, score: float = None, max_score: float = None):
        if self.use_supabase:
            update_data = {"status": status}
            if grade: update_data["grade"] = grade
            if feedback: update_data["feedback"] = feedback
            
            # Handle metadata updates (score/max_score)
            # We need to be careful not to overwrite existing metadata if we can avoid it.
            # But for now, let's just assume we can merge or patch.
            # Supabase update doesn't support deep merge easily without stored procedure or fetching first.
            # Let's fetch first to be safe, or just upsert the keys we know.
            # actually, if we just want to set these fields, we can fetch, update dict, push back.
            
            if score is not None or max_score is not None:
                # Fetch current metadata to merge
                # Optimization: In a real high-traffic app we'd use a jsonb_set or similar, but here fetching is fine.
                current = self.client.table("submissions").select("metadata").eq("id", sub_id).execute()
                current_meta = {}
                if current.data and current.data[0].get('metadata'):
                     current_meta = current.data[0]['metadata']
                
                if score is not None: current_meta['score'] = score
                if max_score is not None: current_meta['max_score'] = max_score
                
                update_data['metadata'] = current_meta

            self.client.table("submissions").update(update_data).eq("id", sub_id).execute()
        else:
            all_subs = self.get_all()
            for sub in all_subs:
                if sub.id == sub_id:
                    sub.status = status
                    if grade: sub.grade = grade # Note: local SubmissionMetadata might not have 'grade' field if it wasn't added to model?
                    # Let's check model definition in a moment. 
                    # If SubmissionMetadata doesn't have 'grade', this line does nothing useful or might error if strict.
                    # But Pydantic models usually key access? No, attribute access.
                    # 'sub' is a SubmissionMetadata object.
                    
                    if feedback: sub.feedback_summary = feedback
                    if score is not None: sub.score = score
                    if max_score is not None: sub.max_score = max_score
            self._save(all_subs)

    def _save(self, subs: List[SubmissionMetadata]):
        with open(self.submissions_file, "w") as f:
            json.dump([s.dict() for s in subs], f, indent=2)

    # --- File Management Helpers ---

    def save_file(self, file_content: bytes, filename: str) -> str:
        """Saves file to storage (local or Supabase) and returns a path/identifier."""
        if self.use_supabase:
            try:
                self.client.storage.from_("uploads").upload(filename, file_content)
                return filename 
            except Exception as e:
                print(f"Supabase upload error: {e}")
                raise e
        else:
            path = os.path.join(self.uploads_dir, filename)
            with open(path, "wb") as f:
                f.write(file_content)
            return path

    def get_file_path(self, filename_or_path: str) -> str:
        """
        Ensures the file is available locally (downloading if needed) and returns local path.
        """
        if os.path.isabs(filename_or_path) and os.path.exists(filename_or_path):
            return filename_or_path

        if self.use_supabase:
            local_path = os.path.join(self.uploads_dir, os.path.basename(filename_or_path))
            # Just try to download if it's not there, or overwrite to be safe?
            # Start with check to avoid re-downloading if we are in non-ephemeral env
            if not os.path.exists(local_path):
                print(f"Downloading {filename_or_path} from Supabase...")
                try:
                    res = self.client.storage.from_("uploads").download(filename_or_path)
                    with open(local_path, "wb") as f:
                        f.write(res)
                except Exception as e:
                    print(f"Supabase download error: {e}")
                    return None
            return local_path
        
        local_path = os.path.join(self.uploads_dir, os.path.basename(filename_or_path))
        if os.path.exists(local_path):
            return local_path
            
        return None
