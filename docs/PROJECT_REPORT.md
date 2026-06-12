# Project Report: Revised Voting System

## Abstract

The Revised Voting System is a software prototype for contactless and fraud-resistant voting. It replaces manual identity checking with iris-based biometric verification and replaces physical EVM buttons with a hand-gesture interface. The goal is to reduce voter verification time, avoid repeated physical contact with machines, prevent double voting, and demonstrate how pattern recognition can support safer public voting infrastructure.

This GitHub version focuses on the examinable software components: iris template matching, gesture classification, SQL voter validation, candidate selection, and vote recording. Physical devices such as an iris scanner, barricade motor, and LED display are represented through Python interfaces so the system can be tested without hardware.

## Introduction

Traditional polling workflows rely on manual identity checks and physical button-based voting machines. These steps can create long queues, require additional manpower, and introduce hygiene concerns when many voters touch the same device. The proposed system allows a voter to be verified using an iris scan, opens access only for eligible voters, and lets the voter cast a vote using a recognized hand gesture.

The prototype is divided into two modules:

1. Biometric identity verification using iris templates.
2. Touchless vote selection using hand gesture recognition.

## Necessity

- Reduce time wasted in manual voter verification.
- Prevent fraudulent voting and double voting.
- Avoid repeated physical contact with voting machines.
- Provide a clean software model for biometric and gesture-based voting.

## Objectives

- Store voter, candidate, eligibility, and voting status in an SQL database.
- Match a scanned iris template against enrolled voter templates.
- Allow booth access only after successful identity and eligibility validation.
- Classify hand gestures for candidate selection and confirmation.
- Record each vote once and reject repeat voting attempts.

## Scope

This repository is a prototype suitable for academic and recruiter review. It demonstrates the algorithmic and database flow but does not claim production election readiness. In a real deployment, the biometric module would be connected to a certified iris scanner SDK, the gesture module could use a webcam with MediaPipe/OpenCV, and the barricade module would send signals to a microcontroller.

## System Modules

### Module 1: Iris-Based Identity Verification

The iris recognition module compares binary iris templates using Hamming distance. A low distance means the scanned pattern is close to the enrolled voter template. If the match is below the configured threshold, the voter is identified.

Implementation file: `voting_system/iris_recognition.py`

Key logic:

- Convert plain grayscale PGM eye images into compact binary texture templates.
- Clean binary iris templates.
- Compare probe and enrolled templates.
- Return best voter match and acceptance status.
- Reject unknown or weak matches.

### Module 2: SQL Voter Validation

The database module stores voters, candidates, and vote records. It validates whether the matched voter is eligible, belongs to a constituency, and has not already voted.

Implementation file: `voting_system/database.py`

Tables:

- `voters`
- `candidates`
- `votes`

### Module 3: Gesture-Based Vote Selection

The gesture recognition module accepts 21 hand landmarks in the same structure used by common hand-tracking systems. It classifies simple voting gestures:

- One finger: candidate 1
- Two fingers: candidate 2
- Three fingers: candidate 3
- Thumbs up: confirm
- Closed fist: cancel or no action

Implementation file: `voting_system/gesture_recognition.py`

### Module 4: Voting Controller

The controller combines biometric matching, voter eligibility checking, candidate selection, vote confirmation, and database update.

Implementation file: `voting_system/controller.py`

## Functional Requirements

- The system shall identify a voter from an iris template.
- The system shall reject unknown voters.
- The system shall reject ineligible voters.
- The system shall reject voters who have already voted.
- The system shall show candidates from the voter's constituency.
- The system shall map hand gestures to candidate choices.
- The system shall record only confirmed votes.

## Non-Functional Requirements

- The prototype should run locally with the Python standard library.
- Biometric templates should be represented as non-image binary codes for demo privacy.
- Vote recording should be transaction-safe through SQLite.
- Pattern-recognition modules should be isolated for future SDK or webcam integration.

## Data Flow

```text
Iris Scan -> Iris Template -> Iris Matching -> Voter Record
    -> Eligibility Check -> Barricade Access -> Gesture Selection
    -> Confirmation Gesture -> Vote Stored -> Voter Marked as Voted
```

## Database Design

```text
voters(voter_id, full_name, aadhaar_last4, constituency, eligible, has_voted, iris_template)
candidates(candidate_id, name, party, constituency)
votes(vote_id, voter_id, candidate_id, cast_at)
```

The `votes.voter_id` column is unique, which creates a database-level protection against double voting.

## Algorithm Summary

### Iris Matching

1. Read the scanned iris template.
2. Compare it with every enrolled iris template.
3. Calculate normalized Hamming distance.
4. Select the closest match.
5. Accept only when distance is below the threshold.

### Gesture Recognition

1. Read 21 hand landmarks.
2. Compare fingertip and joint positions.
3. Count raised fingers.
4. Map the gesture to selection or confirmation.

## How to Run

Graphical interface:

```bash
python3 app.py
```

The GUI provides a voter-facing booth screen. It verifies the sample voter, displays an EVM-style candidate list, captures a live gesture vote, asks for confirmation, and records the vote. Option 10 is NOTA.

For the live demonstration, the system enrolls and verifies a normalized face/eye-region template through OpenCV. Successful matching opens a simulated barricade in the interface. This is a software substitute for a certified iris scanner SDK; a standard webcam cannot reproduce Apple Face ID depth sensing or production iris recognition.

The user interface includes a black-and-white EVM representation. After gesture capture, the selected option is highlighted on the EVM and candidate list before final confirmation. Successful voting preserves the selected candidate on screen and locks the barricade again.

On macOS, the application prefers non-zero camera indexes first to avoid iPhone Continuity Camera when possible. For a guaranteed MacBook-camera demo, Continuity Camera should be disabled on the iPhone.

Command-line interface:

```bash
python3 scripts/seed_database.py
python3 demo.py
python3 -m unittest discover -s tests
```

For live webcam gesture checking:

```bash
python3 -m pip install -r requirements-webcam.txt
python3 webcam_gesture_demo.py
```

The camera uses a large centered capture box. For options 6-10, the voter can use both hands.

Expected demo behavior:

1. Voter is verified.
2. Barricade access is granted.
3. Two-finger gesture selects candidate 2.
4. Thumbs-up gesture confirms the vote.
5. A second attempt by the same voter is rejected.

## Limitations

- Uses simulated iris templates instead of real scanner images.
- Uses generated hand landmarks instead of live webcam input.
- Does not include cryptographic election auditing.
- Does not include hardware integration for a physical barricade.

## Future Enhancements

- Connect an actual iris scanner SDK.
- Add OpenCV preprocessing for live iris segmentation.
- Add MediaPipe webcam hand tracking.
- Add encrypted audit logs and admin dashboards.
- Add microcontroller communication for barricade control.

## References

- J. Daugman, "How Iris Recognition Works", International Conference on Image Processing, 2002.
- Real-time iris localization and iris recognition literature.
- Hand gesture classification using computer vision and landmark-based recognition.
- SQLite documentation for local relational database prototypes.
