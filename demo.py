from __future__ import annotations

from pathlib import Path

from voting_system.controller import RevisedVotingSystem
from voting_system.database import VotingDatabase
from voting_system.gesture_recognition import synthetic_landmarks
from voting_system.iris_recognition import IrisRecognizer


ROOT = Path(__file__).resolve().parent


def main() -> None:
    database = VotingDatabase(ROOT / "revised_voting.db")
    system = RevisedVotingSystem(database)

    probe = IrisRecognizer.read_template(ROOT / "data/iris_templates/scan_voter001.txt")
    verification = system.verify_voter(probe)
    print(verification.message)
    if not verification.allowed or verification.voter is None:
        return

    selected = system.select_candidate(verification.voter, synthetic_landmarks("two"))
    print(f"Gesture selected: {selected.name} ({selected.party})")

    result = system.confirm_and_cast(verification.voter, selected, synthetic_landmarks("thumbs_up"))
    print(result)

    second_try = system.verify_voter(probe)
    print(f"Second attempt: {second_try.message}")


if __name__ == "__main__":
    main()
