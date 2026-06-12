from __future__ import annotations

import sys
from argparse import ArgumentParser
from collections import deque
from pathlib import Path

from webcam_gesture_demo import open_camera


def load_cv2():
    try:
        import cv2
    except ModuleNotFoundError:
        print("Missing package: opencv-python", flush=True)
        print("Install with: python3 -m pip install opencv-python", flush=True)
        sys.exit(1)
    return cv2


def extract_template(cv2, frame, face_cascade, eye_cascade):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(110, 110))
    if len(faces) == 0:
        return None, frame, "Align face inside the box"

    x, y, w, h = sorted(faces, key=lambda item: item[2] * item[3], reverse=True)[0]
    face = gray[y : y + h, x : x + w]
    upper_face = face[: max(1, h // 2), :]
    eyes = eye_cascade.detectMultiScale(upper_face, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))

    # Keep the biometric crop fixed. A crop that changes when eye detection
    # briefly drops out makes consecutive verification frames incomparable.
    template_region = face[: max(1, int(h * 0.68)), :]
    label = "Face and eye-region biometric captured"

    template = cv2.resize(template_region, (120, 80), interpolation=cv2.INTER_AREA)
    template = cv2.equalizeHist(template)

    cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
    for ex, ey, ew, eh in eyes[:2]:
        cv2.rectangle(frame, (x + ex, y + ey), (x + ex + ew, y + ey + eh), (0, 255, 0), 2)

    return template, frame, label


def compare_templates(cv2, enrolled_path: Path, probe) -> float:
    enrolled = cv2.imread(str(enrolled_path), cv2.IMREAD_GRAYSCALE)
    if enrolled is None:
        raise ValueError("No enrolled biometric template found.")

    probe = cv2.resize(probe, (enrolled.shape[1], enrolled.shape[0]), interpolation=cv2.INTER_AREA)
    pixel_result = cv2.matchTemplate(probe, enrolled, cv2.TM_CCOEFF_NORMED)

    enrolled_edges = cv2.Canny(enrolled, 60, 140)
    probe_edges = cv2.Canny(probe, 60, 140)
    edge_result = cv2.matchTemplate(probe_edges, enrolled_edges, cv2.TM_CCOEFF_NORMED)

    pixel_score = max(0.0, float(pixel_result[0][0]))
    edge_score = max(0.0, float(edge_result[0][0]))
    return (pixel_score * 0.75) + (edge_score * 0.25)


def main() -> None:
    parser = ArgumentParser(description="Enroll or verify webcam biometric template.")
    parser.add_argument("--mode", choices=("enroll", "verify"), required=True)
    parser.add_argument("--template", required=True)
    args = parser.parse_args()

    cv2 = load_cv2()
    template_path = Path(args.template)
    template_path.parent.mkdir(parents=True, exist_ok=True)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")
    camera = open_camera(cv2)
    if camera is None:
        print("Could not open Mac camera.", flush=True)
        sys.exit(1)

    enrollment_samples = []
    stable_frames = 0
    last_score = 0.0
    threshold = 0.42
    recent_matches: deque[bool] = deque(maxlen=15)

    while True:
        ok, frame = camera.read()
        if not ok:
            print("Could not read frame from camera.", flush=True)
            break

        frame = cv2.flip(frame, 1)
        height, width = frame.shape[:2]
        cv2.rectangle(
            frame,
            (int(width * 0.22), int(height * 0.14)),
            (int(width * 0.78), int(height * 0.86)),
            (255, 255, 255),
            2,
        )
        template, frame, label = extract_template(cv2, frame, face_cascade, eye_cascade)

        if template is not None:
            if args.mode == "enroll":
                enrollment_samples.append(template.astype("float32"))
                stable_frames += 1
                progress = min(100, int(stable_frames / 20 * 100))
                status = f"Enrolling: {progress}%"
                if stable_frames >= 20:
                    import numpy as np

                    averaged_template = np.mean(enrollment_samples, axis=0).astype("uint8")
                    cv2.imwrite(str(template_path), averaged_template)
                    print(f"BIOMETRIC_ENROLLED:{template_path}", flush=True)
                    break
            else:
                try:
                    last_score = compare_templates(cv2, template_path, template)
                except ValueError as error:
                    print(f"BIOMETRIC_ERROR:{error}", flush=True)
                    break
                recent_matches.append(last_score >= threshold)
                matching_frames = sum(recent_matches)
                progress = min(100, int(matching_frames / 10 * 100))
                status = f"Match {last_score:.2f} | Verification {progress}%"
                if matching_frames >= 10:
                    print(f"BIOMETRIC_VERIFIED:{last_score:.2f}", flush=True)
                    break
        else:
            if args.mode == "verify":
                recent_matches.append(False)
            status = label

        cv2.rectangle(frame, (20, 20), (720, 82), (0, 0, 0), -1)
        cv2.putText(
            frame,
            status,
            (35, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            "Press q to cancel",
            (35, height - 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.75,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("Revised Voting System - Biometric Verification", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
