-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (for application-level user data)
-- Supabase has auth.users for authentication
-- This table is for additional user metadata
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE,
    phone TEXT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Policy: Users can read their own data
CREATE POLICY "Users can view own data"
    ON public.users
    FOR SELECT
    USING (auth.uid()::text = id::text);

-- Policy: Service role can do everything
CREATE POLICY "Service role has full access to users"
    ON public.users
    USING (auth.role() = 'service_role');

-- Requests table (main metrics log)
CREATE TABLE IF NOT EXISTS public.requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    route TEXT,
    prompt TEXT,
    response TEXT,
    tokens_in INTEGER DEFAULT 0,
    tokens_out INTEGER DEFAULT 0,
    cost_usd NUMERIC(12, 6) DEFAULT 0.0,
    latency_ms FLOAT DEFAULT 0.0,
    model TEXT,
    status TEXT DEFAULT 'ok',
    tool_used TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.requests ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view their own requests
CREATE POLICY "Users can view own requests"
    ON public.requests
    FOR SELECT
    USING (auth.uid()::text = user_id::text OR user_id IS NULL);

-- Policy: Authenticated users can insert requests
CREATE POLICY "Authenticated users can insert requests"
    ON public.requests
    FOR INSERT
    WITH CHECK (true);

-- Policy: Service role has full access
CREATE POLICY "Service role has full access to requests"
    ON public.requests
    USING (auth.role() = 'service_role');

-- Tools usage table
CREATE TABLE IF NOT EXISTS public.tools_usage (
    id SERIAL PRIMARY KEY,
    request_id UUID REFERENCES public.requests(id) ON DELETE CASCADE,
    tool_name TEXT,
    duration_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.tools_usage ENABLE ROW LEVEL SECURITY;

-- Policy: Allow read for authenticated users
CREATE POLICY "Authenticated users can view tools_usage"
    ON public.tools_usage
    FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Policy: Allow insert for authenticated users
CREATE POLICY "Authenticated users can insert tools_usage"
    ON public.tools_usage
    FOR INSERT
    WITH CHECK (true);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_requests_created_at ON public.requests(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_requests_user_id ON public.requests(user_id);
CREATE INDEX IF NOT EXISTS idx_requests_status ON public.requests(status);
CREATE INDEX IF NOT EXISTS idx_tools_usage_request_id ON public.tools_usage(request_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON public.users(email);
CREATE INDEX IF NOT EXISTS idx_users_phone ON public.users(phone);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions
GRANT USAGE ON SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated;
