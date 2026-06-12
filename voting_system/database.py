from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Voter:
    voter_id: str
    full_name: str
    constituency: str
    eligible: bool
    has_voted: bool
    iris_template: str


@dataclass(frozen=True)
class Candidate:
    candidate_id: int
    name: str
    party: str
    constituency: str


class VotingDatabase:
    def __init__(self, db_path: str | Path = "revised_voting.db") -> None:
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self, schema_path: str | Path = "sql/schema.sql") -> None:
        with self.connect() as connection:
            connection.executescript(Path(schema_path).read_text(encoding="utf-8"))

    def upsert_voters(self, voters: Iterable[tuple[str, str, str, str, int, int, str]]) -> None:
        query = """
            INSERT INTO voters
                (voter_id, full_name, aadhaar_last4, constituency, eligible, has_voted, iris_template)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(voter_id) DO UPDATE SET
                full_name = excluded.full_name,
                aadhaar_last4 = excluded.aadhaar_last4,
                constituency = excluded.constituency,
                eligible = excluded.eligible,
                has_voted = excluded.has_voted,
                iris_template = excluded.iris_template
        """
        with self.connect() as connection:
            connection.executemany(query, voters)

    def upsert_candidates(self, candidates: Iterable[tuple[int, str, str, str]]) -> None:
        query = """
            INSERT INTO candidates (candidate_id, name, party, constituency)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(candidate_id) DO UPDATE SET
                name = excluded.name,
                party = excluded.party,
                constituency = excluded.constituency
        """
        with self.connect() as connection:
            connection.executemany(query, candidates)

    def list_voters(self) -> list[Voter]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM voters ORDER BY voter_id").fetchall()
        return [self._row_to_voter(row) for row in rows]

    def list_candidates(self, constituency: str) -> list[Candidate]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM candidates WHERE constituency = ? ORDER BY candidate_id",
                (constituency,),
            ).fetchall()
        return [
            Candidate(row["candidate_id"], row["name"], row["party"], row["constituency"])
            for row in rows
        ]

    def get_voter(self, voter_id: str) -> Voter | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM voters WHERE voter_id = ?", (voter_id,)).fetchone()
        return self._row_to_voter(row) if row else None

    def cast_vote(self, voter_id: str, candidate_id: int) -> None:
        with self.connect() as connection:
            voter = connection.execute("SELECT * FROM voters WHERE voter_id = ?", (voter_id,)).fetchone()
            if voter is None:
                raise ValueError("Voter not found.")
            if not voter["eligible"]:
                raise ValueError("Voter is not eligible.")
            if voter["has_voted"]:
                raise ValueError("Voter has already voted.")

            candidate = connection.execute(
                "SELECT * FROM candidates WHERE candidate_id = ? AND constituency = ?",
                (candidate_id, voter["constituency"]),
            ).fetchone()
            if candidate is None:
                raise ValueError("Candidate does not belong to voter's constituency.")

            connection.execute(
                "INSERT INTO votes (voter_id, candidate_id) VALUES (?, ?)",
                (voter_id, candidate_id),
            )
            connection.execute("UPDATE voters SET has_voted = 1 WHERE voter_id = ?", (voter_id,))

    @staticmethod
    def _row_to_voter(row: sqlite3.Row) -> Voter:
        return Voter(
            voter_id=row["voter_id"],
            full_name=row["full_name"],
            constituency=row["constituency"],
            eligible=bool(row["eligible"]),
            has_voted=bool(row["has_voted"]),
            iris_template=row["iris_template"],
        )
