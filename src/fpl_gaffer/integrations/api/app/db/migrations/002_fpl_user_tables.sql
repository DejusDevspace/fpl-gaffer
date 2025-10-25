-- FPL Teams table (links Supabase user to FPL team)
CREATE TABLE IF NOT EXISTS public.fpl_teams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES public.users(id) ON DELETE CASCADE,
    fpl_id INTEGER UNIQUE NOT NULL,
    team_name TEXT,
    player_first_name TEXT,
    player_last_name TEXT,
    years_active INTEGER,
    favourite_team INTEGER,
    started_event INTEGER,
    overall_rank INTEGER,
    overall_points INTEGER,
    current_gameweek INTEGER,
    total_transfers INTEGER DEFAULT 0,
    team_value NUMERIC(10, 1),
    bank NUMERIC(10, 1),
    last_synced_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE public.fpl_teams ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own FPL team"
    ON public.fpl_teams FOR SELECT
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can insert own FPL team"
    ON public.fpl_teams FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

CREATE POLICY "Users can update own FPL team"
    ON public.fpl_teams FOR UPDATE
    USING (auth.uid()::text = user_id::text);

CREATE POLICY "Service role has full access to fpl_teams"
    ON public.fpl_teams
    USING (auth.role() = 'service_role');

-- Gameweek History table
CREATE TABLE IF NOT EXISTS public.gameweek_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fpl_team_id UUID REFERENCES public.fpl_teams(id) ON DELETE CASCADE,
    gameweek INTEGER NOT NULL,
    points INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    rank INTEGER,
    rank_sort INTEGER,
    overall_rank INTEGER,
    percentile_rank NUMERIC(5, 2),
    bank NUMERIC(10, 1),
    team_value NUMERIC(10, 1),
    event_transfers INTEGER DEFAULT 0,
    event_transfers_cost INTEGER DEFAULT 0,
    points_on_bench INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fpl_team_id, gameweek)
);

-- Enable RLS
ALTER TABLE public.gameweek_history ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own gameweek history"
    ON public.gameweek_history FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.fpl_teams
            WHERE fpl_teams.id = gameweek_history.fpl_team_id
            AND fpl_teams.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Service role has full access to gameweek_history"
    ON public.gameweek_history
    USING (auth.role() = 'service_role');

-- Transfer History table
CREATE TABLE IF NOT EXISTS public.transfer_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fpl_team_id UUID REFERENCES public.fpl_teams(id) ON DELETE CASCADE,
    gameweek INTEGER NOT NULL,
    time TIMESTAMPTZ,
    player_in_id INTEGER,
    player_in_name TEXT,
    player_in_cost NUMERIC(10, 1),
    player_out_id INTEGER,
    player_out_name TEXT,
    player_out_cost NUMERIC(10, 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.transfer_history ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own transfer history"
    ON public.transfer_history FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.fpl_teams
            WHERE fpl_teams.id = transfer_history.fpl_team_id
            AND fpl_teams.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Service role has full access to transfer_history"
    ON public.transfer_history
    USING (auth.role() = 'service_role');

-- Captain Picks table (track captain choices per GW)
CREATE TABLE IF NOT EXISTS public.captain_picks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fpl_team_id UUID REFERENCES public.fpl_teams(id) ON DELETE CASCADE,
    gameweek INTEGER NOT NULL,
    player_id INTEGER,
    player_name TEXT,
    is_vice_captain BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(fpl_team_id, gameweek, is_vice_captain)
);

-- Enable RLS
ALTER TABLE public.captain_picks ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Users can view own captain picks"
    ON public.captain_picks FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.fpl_teams
            WHERE fpl_teams.id = captain_picks.fpl_team_id
            AND fpl_teams.user_id::text = auth.uid()::text
        )
    );

CREATE POLICY "Service role has full access to captain_picks"
    ON public.captain_picks
    USING (auth.role() = 'service_role');

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fpl_teams_user_id ON public.fpl_teams(user_id);
CREATE INDEX IF NOT EXISTS idx_fpl_teams_fpl_id ON public.fpl_teams(fpl_id);
CREATE INDEX IF NOT EXISTS idx_gameweek_history_fpl_team_id ON public.gameweek_history(fpl_team_id);
CREATE INDEX IF NOT EXISTS idx_gameweek_history_gameweek ON public.gameweek_history(gameweek);
CREATE INDEX IF NOT EXISTS idx_transfer_history_fpl_team_id ON public.transfer_history(fpl_team_id);
CREATE INDEX IF NOT EXISTS idx_transfer_history_gameweek ON public.transfer_history(gameweek);
CREATE INDEX IF NOT EXISTS idx_captain_picks_fpl_team_id ON public.captain_picks(fpl_team_id);

-- Function to update updated_at timestamp
CREATE TRIGGER update_fpl_teams_updated_at
    BEFORE UPDATE ON public.fpl_teams
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
