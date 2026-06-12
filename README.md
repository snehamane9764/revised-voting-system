# Revised Voting System

Python prototype for a contactless voting system using iris-based voter verification, gesture-based vote selection, and an SQLite voter database.

This repository is designed as a recruiter-reviewable version of the academic project. It does not require a physical iris scanner, barricade motor, or biometric SDK. Hardware calls are represented by clean Python interfaces and sample data so the pattern-recognition logic and database flow can be examined.

## Features

- Iris template matching using binary iris codes and Hamming distance.
- Dependency-free grayscale PGM image-to-iris-template extractor for demo scans.
- SQLite voter database with eligibility and double-voting checks.
- Gesture recognition from MediaPipe-style 21-point hand landmarks.
- End-to-end voting controller that simulates barricade access and vote casting.
- Sample seed data and unit tests.

## Project Flow

1. Voter presents iris scan.
2. System extracts or receives an iris template.
3. Template is matched against registered voters.
4. Database validates eligibility and whether the voter has already voted.
5. Barricade access is granted only after successful validation.
6. Voter selects a candidate through hand gesture.
7. Confirmation gesture records the vote and locks the voter from voting again.

## Quick Start

Open the voter-facing desktop GUI:

```bash
python3 app.py
```

The GUI shows an EVM-style candidate list after voter verification. The voter can select an option by showing the option number through hand gestures. Option 10 is NOTA.

The booth now includes local biometric enrollment and verification. A Mac webcam captures a normalized face/eye-region template, verifies it on the next scan, and changes the simulated barricade from locked to open. The captured biometric file stays under `data/biometric/` and is excluded from Git.

After verification, the interface changes the barricade to `UNLOCKED` and enables a centered EVM machine visual. A detected gesture highlights the selected EVM option and candidate before confirmation, and the recorded selection remains visible after voting.

The app tries to skip iPhone Continuity Camera by preferring other camera indexes first. For a permanent Mac-only setup, turn off Continuity Camera on the iPhone:

`Settings > General > AirPlay & Continuity > Continuity Camera > Off`

Command-line option:

```bash
python3 scripts/seed_database.py
python3 demo.py
python3 -m unittest discover -s tests
```

## Live Webcam Gesture Demo

Install the optional camera packages:

```bash
python3 -m pip install -r requirements-webcam.txt
```

Run the live checker:

```bash
python3 webcam_gesture_demo.py
```

Your webcam window will show the detected gesture. Press `q` to close it.

In GUI voting mode, the camera uses a large centered capture box. Keep only your hand or hands inside the box. For options 6-10, show both hands and hold the gesture steady until the capture completes.

## Example Gestures

- `one`: candidate 1
- `two`: candidate 2
- `three`: candidate 3
- `4` to `10`: additional candidate options using finger count
- `thumbs_up`: confirm vote
- `closed_fist`: cancel or no action

## Iris Recognition Note

The project supports two prototype inputs:

- Existing binary iris templates, similar to what a biometric SDK could return.
- Plain PGM grayscale eye images, converted into a compact binary texture template.

The live GUI uses OpenCV face and eye detection because a normal Mac webcam cannot perform certified iris scanning or Apple Face ID depth sensing. The code keeps this adapter separate so a real iris scanner SDK can replace it later.

## Repository Structure

```text
voting_system/
  database.py             SQLite access layer
  iris_recognition.py     Iris-code matching logic
  gesture_recognition.py  Hand-landmark gesture classifier
  controller.py           End-to-end voting workflow
scripts/
  seed_database.py        Creates sample SQLite database
sql/
  schema.sql              Database tables and constraints
docs/
  PROJECT_REPORT.md       GitHub-friendly project report
tests/
  test_voting_flow.py     Core behavior tests
data/
  iris_templates/         Sample enrolled and scanned iris codes
  landmarks/              Sample hand landmark files
```

## Technology Used

- Python 3
- SQLite
- Pattern recognition algorithms
- Biometric-template matching
- MediaPipe-compatible hand landmark model

## Note

This is a software prototype. A production election system would require certified biometric hardware, secure key management, audit trails, tamper-resistant infrastructure, privacy review, and legal approval.
