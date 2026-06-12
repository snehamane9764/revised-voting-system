PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS voters (
    voter_id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    aadhaar_last4 TEXT NOT NULL,
    constituency TEXT NOT NULL,
    eligible INTEGER NOT NULL CHECK (eligible IN (0, 1)),
    has_voted INTEGER NOT NULL DEFAULT 0 CHECK (has_voted IN (0, 1)),
    iris_template TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    party TEXT NOT NULL,
    constituency TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_id TEXT NOT NULL UNIQUE,
    candidate_id INTEGER NOT NULL,
    cast_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (voter_id) REFERENCES voters(voter_id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
);

