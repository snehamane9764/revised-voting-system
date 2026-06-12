from __future__ import annotations

from dataclasses import dataclass

from voting_system.database import Candidate, VotingDatabase, Voter
from voting_system.gesture_recognition import GestureRecognizer, Point
from voting_system.iris_recognition import IrisRecognizer


@dataclass(frozen=True)
class VerificationResult:
    allowed: bool
    message: str
    voter: Voter | None = None


class RevisedVotingSystem:
    def __init__(
        self,
        database: VotingDatabase,
        iris_recognizer: IrisRecognizer | None = None,
        gesture_recognizer: GestureRecognizer | None = None,
    ) -> None:
        self.database = database
        self.iris_recognizer = iris_recognizer or IrisRecognizer()
        self.gesture_recognizer = gesture_recognizer or GestureRecognizer()

    def verify_voter(self, probe_iris_template: str) -> VerificationResult:
        enrolled = {voter.voter_id: voter.iris_template for voter in self.database.list_voters()}
        match = self.iris_recognizer.identify(probe_iris_template, enrolled)
        if match is None or not match.accepted:
            return VerificationResult(False, "Iris verification failed.")

        voter = self.database.get_voter(match.voter_id)
        if voter is None:
            return VerificationResult(False, "Matched voter record was not found.")
        if not voter.eligible:
            return VerificationResult(False, "Voter is not eligible.", voter)
        if voter.has_voted:
            return VerificationResult(False, "Voter has already voted.", voter)

        return VerificationResult(
            True,
            f"Verified {voter.full_name}. Barricade access granted.",
            voter,
        )

    def candidates_for_voter(self, voter: Voter) -> list[Candidate]:
        return self.database.list_candidates(voter.constituency)

    def select_candidate(self, voter: Voter, landmarks: list[Point]) -> Candidate:
        gesture = self.gesture_recognizer.classify(landmarks)
        gesture_to_position = {"one": 0, "two": 1, "three": 2}
        if gesture not in gesture_to_position:
            raise ValueError(f"Gesture {gesture!r} is not a candidate selection.")

        candidates = self.candidates_for_voter(voter)
        position = gesture_to_position[gesture]
        if position >= len(candidates):
            raise ValueError("Selected gesture does not map to an available candidate.")
        return candidates[position]

    def confirm_and_cast(self, voter: Voter, candidate: Candidate, landmarks: list[Point]) -> str:
        gesture = self.gesture_recognizer.classify(landmarks)
        if gesture != "thumbs_up":
            raise ValueError("Vote was not confirmed.")

        self.database.cast_vote(voter.voter_id, candidate.candidate_id)
        return f"Vote recorded for {candidate.name} ({candidate.party})."
