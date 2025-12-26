-- Create the submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY,
    filename TEXT NOT NULL,
    assignment_type TEXT NOT NULL,
    student_id TEXT,
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'PENDING',
    grade TEXT,
    feedback TEXT,
    rubric_path TEXT,
    metadata JSONB
);

-- Enable Row Level Security (RLS)
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows anyone to insert/select/update (for demo purposes)
-- IN PRODUCTION: You should restrict this to authenticated users!
CREATE POLICY "Public Access" ON submissions FOR ALL USING (true);

-- Create a storage bucket for uploads
INSERT INTO storage.buckets (id, name, public) VALUES ('uploads', 'uploads', true)
ON CONFLICT (id) DO NOTHING;

-- Create storage policy to allow public uploads/downloads (for demo purposes)
-- IN PRODUCTION: Restrict this!
CREATE POLICY "Public Storage Access" ON storage.objects FOR ALL USING ( bucket_id = 'uploads' );
