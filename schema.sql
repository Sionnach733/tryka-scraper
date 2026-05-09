CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL UNIQUE,
    race_name TEXT NOT NULL,
    division TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    idp TEXT NOT NULL,
    event_id INTEGER NOT NULL REFERENCES events(id),
    -- Athlete / team info
    members TEXT NOT NULL,           -- JSON array of member name strings
    bib_number TEXT,
    gym_affiliate TEXT,
    age_group TEXT,
    gender TEXT,                     -- M / W / X (mixed) inferred from event or page
    -- Rankings
    rank_overall INTEGER,
    rank_age_group INTEGER,
    league_points INTEGER,
    overall_time TEXT,
    penalty TEXT,
    bonus TEXT,
    disqual_reason TEXT,
    UNIQUE(idp, event_id)
);

CREATE TABLE IF NOT EXISTS raw_splits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES results(id),
    split_order INTEGER NOT NULL,
    split_name TEXT NOT NULL,
    time_of_day TEXT,
    time TEXT,
    diff TEXT
);

CREATE TABLE IF NOT EXISTS refined_splits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id INTEGER NOT NULL REFERENCES results(id),
    split_order INTEGER NOT NULL,
    split_name TEXT NOT NULL,
    time TEXT,
    place INTEGER                    -- NULL for running/transition segments
);

CREATE INDEX IF NOT EXISTS idx_results_event ON results(event_id);
CREATE INDEX IF NOT EXISTS idx_results_event_gender ON results(event_id, gender);
CREATE INDEX IF NOT EXISTS idx_results_idp ON results(idp);
CREATE INDEX IF NOT EXISTS idx_raw_splits_result ON raw_splits(result_id);
CREATE INDEX IF NOT EXISTS idx_refined_splits_result ON refined_splits(result_id);
