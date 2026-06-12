from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float = 0.0


class GestureRecognizer:
    """Rule-based classifier for MediaPipe-style hand landmarks.

    The expected input is 21 landmarks. The y-axis follows the common camera
    coordinate convention where smaller y values are higher in the image.
    """

    finger_tips = {"index": 8, "middle": 12, "ring": 16, "pinky": 20}
    finger_pips = {"index": 6, "middle": 10, "ring": 14, "pinky": 18}

    def classify(self, landmarks: list[Point]) -> str:
        if len(landmarks) != 21:
            raise ValueError("Expected 21 hand landmarks.")

        raised = self.raised_fingers(landmarks)
        raised_count = sum(raised.values())

        if self._is_thumbs_up(landmarks, raised_count):
            return "thumbs_up"
        if raised_count == 0:
            return "closed_fist"
        if raised["index"] and raised_count == 1:
            return "one"
        if raised["index"] and raised["middle"] and raised_count == 2:
            return "two"
        if raised["index"] and raised["middle"] and raised["ring"] and raised_count == 3:
            return "three"
        return "unknown"

    def raised_fingers(self, landmarks: list[Point]) -> dict[str, bool]:
        return {
            finger: landmarks[self.finger_tips[finger]].y < landmarks[self.finger_pips[finger]].y
            for finger in self.finger_tips
        }

    @staticmethod
    def _is_thumbs_up(landmarks: list[Point], raised_count: int) -> bool:
        thumb_tip = landmarks[4]
        thumb_ip = landmarks[3]
        index_mcp = landmarks[5]
        wrist = landmarks[0]
        thumb_is_high = thumb_tip.y < thumb_ip.y < index_mcp.y
        thumb_is_vertical = abs(thumb_tip.x - wrist.x) < 0.22
        return raised_count == 0 and thumb_is_high and thumb_is_vertical


def load_landmarks(path: str | Path) -> list[Point]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return [Point(float(item["x"]), float(item["y"]), float(item.get("z", 0.0))) for item in raw]


def synthetic_landmarks(gesture: str) -> list[Point]:
    """Creates simple landmark samples for tests and CLI demos."""

    points = [Point(0.5, 0.9) for _ in range(21)]
    for index, (x, y) in {
        0: (0.50, 0.90),
        3: (0.45, 0.74),
        4: (0.42, 0.70),
        5: (0.43, 0.68),
        6: (0.43, 0.58),
        8: (0.43, 0.75),
        9: (0.50, 0.67),
        10: (0.50, 0.57),
        12: (0.50, 0.76),
        13: (0.57, 0.68),
        14: (0.57, 0.58),
        16: (0.57, 0.77),
        17: (0.64, 0.70),
        18: (0.64, 0.60),
        20: (0.64, 0.79),
    }.items():
        points[index] = Point(x, y)

    raised_tips = {
        "one": [8],
        "two": [8, 12],
        "three": [8, 12, 16],
        "closed_fist": [],
        "thumbs_up": [],
    }.get(gesture, [])

    mutable = list(points)
    for tip in raised_tips:
        mutable[tip] = Point(mutable[tip].x, 0.30)

    if gesture == "thumbs_up":
        mutable[4] = Point(0.50, 0.32)
        mutable[3] = Point(0.50, 0.48)
        mutable[5] = Point(0.50, 0.66)

    return mutable
