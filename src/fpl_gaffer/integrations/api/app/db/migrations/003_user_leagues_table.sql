-- User Leagues table (stores leagues for each FPL team)
CREATE TABLE IF NOT EXISTS public.user_leagues (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fpl_team_id UUID REFERENCES public.fpl_teams(id) ON DELETE CASCADE,
    league_id INTEGER NOT NULL,
    league_name TEXT,
    league_type TEXT CHECK (league_type IN ('classic', 'h2h')),
    created TIMESTAMPTZ,
    start_event INTEGER,
    entry_rank INTEGER,
    entry_last_rank INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.user_leagues ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own leagues"
    ON public.user_leagues FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.fpl_teams
            WHERE fpl_teams.id = user_leagues.fpl_team_id
            AND fpl_teams.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Service role has full access to user_leagues"
    ON public.user_leagues
    USING (auth.role() = 'service_role');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_leagues_fpl_team_id ON public.user_leagues(fpl_team_id);
CREATE INDEX IF NOT EXISTS idx_user_leagues_league_id ON public.user_leagues(league_id);
CREATE INDEX IF NOT EXISTS idx_user_leagues_league_type ON public.user_leagues(league_type);

-- Trigger to update updated_at timestamp
CREATE TRIGGER update_user_leagues_updated_at
    BEFORE UPDATE ON public.user_leagues
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
