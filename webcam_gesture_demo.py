from __future__ import annotations

import math
import sys
from argparse import ArgumentParser

from voting_system.gesture_recognition import GestureRecognizer, Point


def import_camera_dependencies():
    try:
        import cv2
    except ModuleNotFoundError as error:
        print(f"Missing package: {error.name}")
        print()
        print("Install webcam dependency with:")
        print("  python3 -m pip install opencv-python")
        sys.exit(1)

    try:
        import mediapipe as mp
    except ModuleNotFoundError:
        return cv2, None

    if not hasattr(mp, "solutions"):
        return cv2, None
    return cv2, mp


def to_points(hand_landmarks) -> list[Point]:
    return [Point(landmark.x, landmark.y, landmark.z) for landmark in hand_landmarks.landmark]


def classify_with_opencv(cv2, frame, max_selection: int = 10) -> tuple[str, int, object]:
    height, width = frame.shape[:2]
    x1 = int(width * 0.12)
    y1 = int(height * 0.14)
    x2 = int(width * 0.88)
    y2 = int(height * 0.86)
    roi = frame[y1:y2, x1:x2]

    ycrcb = cv2.cvtColor(roi, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(ycrcb, (0, 133, 77), (255, 173, 127))
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    hand_contours = [contour for contour in contours if cv2.contourArea(contour) > 4500]
    hand_contours = sorted(hand_contours, key=cv2.contourArea, reverse=True)[:2]

    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 3)
    if not hand_contours:
        cv2.putText(
            frame,
            "Place hand inside the box",
            (x1 + 20, y1 - 15),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
        return "no_hand", 0, frame

    total_fingers = 0
    for contour in hand_contours:
        contour[:, 0, 0] += x1
        contour[:, 0, 1] += y1
        count, frame = count_fingers_for_contour(cv2, frame, contour)
        total_fingers += count

    total_fingers = max(0, min(total_fingers, max_selection))
    if total_fingers == 0:
        gesture = "closed_fist"
    elif total_fingers == 1:
        gesture = "one"
    elif total_fingers == 2:
        gesture = "two"
    elif total_fingers == 3:
        gesture = "three"
    else:
        gesture = f"{total_fingers}_fingers"

    cv2.putText(
        frame,
        "Keep only your hand(s) inside the box. For 6-10, use both hands.",
        (x1 + 20, y2 + 32 if y2 + 32 < height else height - 20),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return gesture, total_fingers, frame


def count_fingers_for_contour(cv2, frame, contour) -> tuple[int, object]:
    hull_points = cv2.convexHull(contour)
    hull_indexes = cv2.convexHull(contour, returnPoints=False)

    finger_gaps = 0
    if hull_indexes is not None and len(hull_indexes) > 3:
        defects = cv2.convexityDefects(contour, hull_indexes)
        if defects is not None:
            for defect in defects[:, 0]:
                start_index, end_index, far_index, depth = defect
                start = contour[start_index][0]
                end = contour[end_index][0]
                far = contour[far_index][0]

                a = distance(start, end)
                b = distance(far, start)
                c = distance(end, far)
                if b == 0 or c == 0:
                    continue

                cosine = max(-1.0, min(1.0, (b * b + c * c - a * a) / (2 * b * c)))
                angle = math.degrees(math.acos(cosine))
                if angle < 95 and depth > 6500:
                    finger_gaps += 1
                    cv2.circle(frame, tuple(far), 5, (0, 0, 255), -1)

    x, y, w, h = cv2.boundingRect(contour)
    hull_tip_count = estimate_fingertips_from_hull(hull_points, y, h)
    defect_count = min(finger_gaps + 1, 5)
    finger_count = max(defect_count, hull_tip_count)

    if finger_gaps == 0 and h < 0.75 * w:
        finger_count = 0

    finger_count = min(max(finger_count, 0), 5)
    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
    cv2.drawContours(frame, [hull_points], -1, (255, 0, 0), 2)
    cv2.putText(
        frame,
        str(finger_count),
        (x, max(30, y - 12)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 255),
        2,
        cv2.LINE_AA,
    )
    return finger_count, frame


def distance(first, second) -> float:
    return ((second[0] - first[0]) ** 2 + (second[1] - first[1]) ** 2) ** 0.5


def estimate_fingertips_from_hull(hull_points, hand_top: int, hand_height: int) -> int:
    points = sorted((tuple(point[0]) for point in hull_points), key=lambda item: item[0])
    if not points:
        return 0

    upper_limit = hand_top + int(hand_height * 0.48)
    candidate_tips = [point for point in points if point[1] <= upper_limit]
    if not candidate_tips:
        return 0

    groups: list[list[tuple[int, int]]] = []
    for point in candidate_tips:
        if not groups or abs(point[0] - groups[-1][-1][0]) > 35:
            groups.append([point])
        else:
            groups[-1].append(point)

    fingertips = [min(group, key=lambda item: item[1]) for group in groups]
    return min(len(fingertips), 5)


def open_camera(cv2, preferred_index: int | None = None):
    backends = []
    if hasattr(cv2, "CAP_AVFOUNDATION"):
        backends.append(cv2.CAP_AVFOUNDATION)
    backends.append(cv2.CAP_ANY)

    # On this macOS setup, iPhone Continuity Camera occupies index 0. Automatic
    # selection deliberately excludes it and only checks local camera indexes.
    camera_indexes = [preferred_index] if preferred_index is not None else [1, 2, 3]
    for backend in backends:
        for camera_index in camera_indexes:
            camera = cv2.VideoCapture(camera_index, backend)
            if not camera.isOpened():
                camera.release()
                continue

            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            for _ in range(20):
                ok, frame = camera.read()
                if ok and frame is not None and frame.size > 0:
                    print(f"Using camera index {camera_index}.", flush=True)
                    return camera
            camera.release()

    return None


def main() -> None:
    parser = ArgumentParser(description="Live webcam gesture checker.")
    parser.add_argument("--camera-index", type=int, default=None)
    parser.add_argument("--selection-mode", action="store_true")
    parser.add_argument("--max-selection", type=int, default=10)
    args = parser.parse_args()

    cv2, mp = import_camera_dependencies()
    recognizer = GestureRecognizer()

    hands = None
    drawing = None
    hand_connections = None
    if mp is not None:
        hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=2,
            model_complexity=1,
            min_detection_confidence=0.65,
            min_tracking_confidence=0.65,
        )
        drawing = mp.solutions.drawing_utils
        hand_connections = mp.solutions.hands.HAND_CONNECTIONS

    camera = open_camera(cv2, preferred_index=args.camera_index)
    if camera is None:
        print("Could not open webcam. Check macOS camera permission for Terminal.", flush=True)
        sys.exit(1)

    print("Live gesture camera started.", flush=True)
    if hands is None:
        print("OpenCV mode: place hand(s) inside the large box. For 6-10, show both hands.", flush=True)
    else:
        print("MediaPipe mode: landmark-based gesture detection.", flush=True)
    print("Hold your gesture steady. Press q to quit.", flush=True)

    stable_count = None
    stable_frames = 0

    while True:
        ok, frame = camera.read()
        if not ok:
            print("Could not read frame from webcam.", flush=True)
            break

        frame = cv2.flip(frame, 1)
        if hands is None:
            gesture, count, frame = classify_with_opencv(cv2, frame, args.max_selection)
        else:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(rgb_frame)
            gesture = "no_hand"
            count = 0
            if result.multi_hand_landmarks:
                for hand_landmarks in result.multi_hand_landmarks:
                    landmarks = to_points(hand_landmarks)
                    hand_gesture = recognizer.classify(landmarks)
                    count += {"one": 1, "two": 2, "three": 3}.get(hand_gesture, 0)
                    drawing.draw_landmarks(frame, hand_landmarks, hand_connections)
                gesture = f"{count}_fingers" if count else "unknown"

        if args.selection_mode and 1 <= count <= args.max_selection:
            if count == stable_count:
                stable_frames += 1
            else:
                stable_count = count
                stable_frames = 1
        else:
            stable_count = None
            stable_frames = 0

        if args.selection_mode and stable_count is not None:
            progress = min(100, int(stable_frames / 30 * 100))
            label = f"Hold option {stable_count}: {progress}%"
            if stable_frames >= 30:
                print(f"FINAL_SELECTION:{stable_count}", flush=True)
                break
        else:
            label = f"Detected: {gesture}"

        cv2.rectangle(frame, (20, 20), (560, 85), (0, 0, 0), -1)
        cv2.putText(
            frame,
            label,
            (35, 58),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

        cv2.imshow("Revised Voting System - Gesture Capture", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    camera.release()
    if hands is not None:
        hands.close()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
