from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class IrisMatch:
    voter_id: str
    distance: float
    accepted: bool


class IrisRecognizer:
    """Prototype iris matcher using binary iris codes and Hamming distance.

    A real scanner SDK would provide an iris image or normalized iris code. This
    prototype focuses on the pattern-recognition step that compares a probe code
    against enrolled templates.
    """

    def __init__(self, threshold: float = 0.22) -> None:
        self.threshold = threshold

    def identify(self, probe_template: str, enrolled: dict[str, str]) -> IrisMatch | None:
        if not enrolled:
            return None

        best_voter_id = ""
        best_distance = 1.0
        for voter_id, template in enrolled.items():
            distance = self.hamming_distance(probe_template, template)
            if distance < best_distance:
                best_voter_id = voter_id
                best_distance = distance

        return IrisMatch(
            voter_id=best_voter_id,
            distance=best_distance,
            accepted=best_distance <= self.threshold,
        )

    @staticmethod
    def hamming_distance(first: str, second: str) -> float:
        a = "".join(ch for ch in first if ch in "01")
        b = "".join(ch for ch in second if ch in "01")
        if not a or not b:
            raise ValueError("Iris templates must contain binary digits.")
        length = min(len(a), len(b))
        mismatches = sum(1 for left, right in zip(a[:length], b[:length]) if left != right)
        mismatches += abs(len(a) - len(b))
        return mismatches / max(len(a), len(b))

    @staticmethod
    def template_from_secret(seed: str, bits: int = 256) -> str:
        """Creates deterministic demo iris codes for test data.

        This is not biometric enrollment. It simply gives the demo stable binary
        templates without storing real biometric data in the repository.
        """

        output = []
        counter = 0
        while len(output) < bits:
            digest = hashlib.sha256(f"{seed}:{counter}".encode("utf-8")).digest()
            for byte in digest:
                output.extend("1" if byte & (1 << bit) else "0" for bit in range(8))
            counter += 1
        return "".join(output[:bits])

    @staticmethod
    def read_template(path: str | Path) -> str:
        return "".join(ch for ch in Path(path).read_text(encoding="utf-8") if ch in "01")

    @staticmethod
    def write_template(path: str | Path, template: str, width: int = 64) -> None:
        cleaned = "".join(ch for ch in template if ch in "01")
        lines = [cleaned[index : index + width] for index in range(0, len(cleaned), width)]
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")

    @staticmethod
    def template_from_pgm(path: str | Path, samples: int = 256) -> str:
        """Extracts a compact binary texture code from a plain PGM eye image.

        This lightweight extractor keeps the repository dependency-free. It reads
        a P2 grayscale image, samples the central eye region, and encodes local
        intensity changes as a binary texture pattern. In production this step is
        where scanner SDK output, iris segmentation, normalization, and Gabor
        filtering would be connected.
        """

        width, height, pixels = IrisRecognizer._read_p2_pgm(path)
        left = width // 4
        right = width - left
        top = height // 4
        bottom = height - top

        values: list[int] = []
        for row in range(top, bottom):
            start = row * width
            values.extend(pixels[start + left : start + right])

        if len(values) < 2:
            raise ValueError("PGM image is too small to extract an iris template.")

        step = max(1, len(values) // samples)
        sampled = values[::step][: samples + 1]
        mean = sum(sampled) / len(sampled)

        bits = []
        for index, value in enumerate(sampled[:samples]):
            neighbor = sampled[(index + 1) % len(sampled)]
            bits.append("1" if (value - neighbor) > 0 or value > mean else "0")
        return "".join(bits)

    @staticmethod
    def _read_p2_pgm(path: str | Path) -> tuple[int, int, list[int]]:
        tokens: list[str] = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            tokens.extend(line.split("#", 1)[0].split())

        if not tokens or tokens[0] != "P2":
            raise ValueError("Only plain-text P2 PGM images are supported.")

        width = int(tokens[1])
        height = int(tokens[2])
        max_value = int(tokens[3])
        if max_value <= 0:
            raise ValueError("Invalid PGM max value.")

        raw_pixels = [int(token) for token in tokens[4:]]
        expected = width * height
        if len(raw_pixels) != expected:
            raise ValueError(f"Expected {expected} pixels, found {len(raw_pixels)}.")

        pixels = [round(pixel * 255 / max_value) for pixel in raw_pixels]
        return width, height, pixels
