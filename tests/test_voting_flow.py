from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from voting_system.controller import RevisedVotingSystem
from voting_system.database import VotingDatabase
from voting_system.gesture_recognition import GestureRecognizer, synthetic_landmarks
from voting_system.iris_recognition import IrisRecognizer


ROOT = Path(__file__).resolve().parents[1]


class RevisedVotingSystemTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.database = VotingDatabase(self.db_path)
        self.database.initialize(ROOT / "sql/schema.sql")
        self.template = IrisRecognizer.template_from_secret("test-voter")
        self.database.upsert_voters(
            [("V001", "Test Voter", "1234", "Test-Constituency", 1, 0, self.template)]
        )
        self.database.upsert_candidates(
            [
                (1, "Candidate One", "Party A", "Test-Constituency"),
                (2, "Candidate Two", "Party B", "Test-Constituency"),
                (3, "Candidate Three", "Party C", "Test-Constituency"),
            ]
        )
        self.system = RevisedVotingSystem(self.database)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_iris_match_allows_eligible_voter_once(self) -> None:
        verification = self.system.verify_voter(self.template)
        self.assertTrue(verification.allowed)
        self.assertIsNotNone(verification.voter)

        candidate = self.system.select_candidate(verification.voter, synthetic_landmarks("two"))
        self.assertEqual(candidate.candidate_id, 2)

        message = self.system.confirm_and_cast(
            verification.voter,
            candidate,
            synthetic_landmarks("thumbs_up"),
        )
        self.assertIn("Vote recorded", message)

        second_attempt = self.system.verify_voter(self.template)
        self.assertFalse(second_attempt.allowed)
        self.assertIn("already voted", second_attempt.message)

    def test_unknown_iris_is_rejected(self) -> None:
        unknown = IrisRecognizer.template_from_secret("unknown")
        verification = self.system.verify_voter(unknown)
        self.assertFalse(verification.allowed)

    def test_gesture_classifier(self) -> None:
        recognizer = GestureRecognizer()
        self.assertEqual(recognizer.classify(synthetic_landmarks("one")), "one")
        self.assertEqual(recognizer.classify(synthetic_landmarks("two")), "two")
        self.assertEqual(recognizer.classify(synthetic_landmarks("three")), "three")
        self.assertEqual(recognizer.classify(synthetic_landmarks("thumbs_up")), "thumbs_up")


if __name__ == "__main__":
    unittest.main()
