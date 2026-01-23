-- =============================================================================
-- Supabase Row Level Security (RLS) Policies for AI Horizon
-- =============================================================================
--
-- Run these SQL statements in your Supabase SQL Editor:
-- 1. Go to Supabase Dashboard > SQL Editor
-- 2. Copy and paste this entire file
-- 3. Click "Run"
--
-- These policies implement:
-- - Service role has full access (for backend API)
-- - Anonymous users have read-only access (public data)
-- - Prevent unauthorized writes from client-side
--
-- =============================================================================

-- Step 1: Enable RLS on the document_registry table
-- This is required before any policies take effect
ALTER TABLE document_registry ENABLE ROW LEVEL SECURITY;

-- Step 2: Allow service role FULL access
-- The backend API uses the service_role key and needs unrestricted access
-- Note: service_role bypasses RLS by default, but explicit policy is good documentation
CREATE POLICY "Service role has full access"
ON document_registry
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Step 3: Allow authenticated users to READ all data
-- Users who are logged in can view all documents
CREATE POLICY "Authenticated users can read all documents"
ON document_registry
FOR SELECT
TO authenticated
USING (true);

-- Step 4: Allow anonymous users to READ all data (public access)
-- Since this is a public research portal, anonymous read access is allowed
CREATE POLICY "Anonymous users can read all documents"
ON document_registry
FOR SELECT
TO anon
USING (true);

-- Step 5: DENY anonymous users from INSERTING data
-- Prevents client-side writes without going through the API
CREATE POLICY "Deny anonymous inserts"
ON document_registry
FOR INSERT
TO anon
WITH CHECK (false);

-- Step 6: DENY anonymous users from UPDATING data
CREATE POLICY "Deny anonymous updates"
ON document_registry
FOR UPDATE
TO anon
USING (false)
WITH CHECK (false);

-- Step 7: DENY anonymous users from DELETING data
CREATE POLICY "Deny anonymous deletes"
ON document_registry
FOR DELETE
TO anon
USING (false);

-- =============================================================================
-- Verification Queries (run these to confirm RLS is working)
-- =============================================================================

-- Check if RLS is enabled on the table
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public' AND tablename = 'document_registry';

-- List all policies on the table
-- SELECT policyname, permissive, roles, cmd, qual, with_check
-- FROM pg_policies
-- WHERE tablename = 'document_registry';

-- =============================================================================
-- Optional: Additional Security Recommendations
-- =============================================================================

-- If you add user accounts in the future, you can add policies like:
--
-- Allow authenticated users to insert their own documents:
-- CREATE POLICY "Users can insert own documents"
-- ON document_registry
-- FOR INSERT
-- TO authenticated
-- WITH CHECK (auth.uid() = user_id);
--
-- Allow users to update only their own documents:
-- CREATE POLICY "Users can update own documents"
-- ON document_registry
-- FOR UPDATE
-- TO authenticated
-- USING (auth.uid() = user_id)
-- WITH CHECK (auth.uid() = user_id);
--
-- Allow users to delete only their own documents:
-- CREATE POLICY "Users can delete own documents"
-- ON document_registry
-- FOR DELETE
-- TO authenticated
-- USING (auth.uid() = user_id);
