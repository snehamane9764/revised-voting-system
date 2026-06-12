from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from voting_system.database import VotingDatabase
from voting_system.iris_recognition import IrisRecognizer


DB_PATH = ROOT / "revised_voting.db"


def main() -> None:
    database = VotingDatabase(DB_PATH)
    database.initialize(ROOT / "sql/schema.sql")
    with database.connect() as connection:
        connection.execute("DELETE FROM votes")

    sneha_template = IrisRecognizer.template_from_secret("sneha-demo-voter")
    shlok_template = IrisRecognizer.template_from_secret("shlok-demo-voter")
    ineligible_template = IrisRecognizer.template_from_secret("ineligible-demo-voter")

    database.upsert_voters(
        [
            ("VOTER001", "Sneha Mane", "1004", "Aurangabad-Central", 1, 0, sneha_template),
            ("VOTER002", "Shlok Goud", "0001", "Aurangabad-Central", 1, 0, shlok_template),
            ("VOTER003", "Sample Ineligible Voter", "9999", "Aurangabad-Central", 0, 0, ineligible_template),
        ]
    )
    database.upsert_candidates(
        [
            (1, "Candidate A", "Party Alpha", "Aurangabad-Central"),
            (2, "Candidate B", "Party Beta", "Aurangabad-Central"),
            (3, "Candidate C", "Party Gamma", "Aurangabad-Central"),
            (4, "Candidate D", "Party Delta", "Aurangabad-Central"),
            (5, "Candidate E", "Party Epsilon", "Aurangabad-Central"),
            (6, "Candidate F", "Party Zeta", "Aurangabad-Central"),
            (7, "Candidate G", "Party Eta", "Aurangabad-Central"),
            (8, "Candidate H", "Party Theta", "Aurangabad-Central"),
            (9, "Candidate I", "Party Iota", "Aurangabad-Central"),
            (10, "NOTA", "None of the Above", "Aurangabad-Central"),
        ]
    )

    template_dir = ROOT / "data/iris_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    IrisRecognizer.write_template(template_dir / "registered_voter001.txt", sneha_template)
    IrisRecognizer.write_template(template_dir / "scan_voter001.txt", sneha_template)
    IrisRecognizer.write_template(
        template_dir / "unknown_scan.txt",
        IrisRecognizer.template_from_secret("unknown-person"),
    )

    print(f"Database created at {DB_PATH}")


if __name__ == "__main__":
    main()
