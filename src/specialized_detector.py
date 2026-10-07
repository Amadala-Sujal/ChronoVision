from pathlib import Path
import cv2
from ultralytics import YOLO


MODEL_PATH = Path(
    r"C:\Users\O\ChronoVision\runs\detect\runs\chronovision\construction_safety\weights\best.pt"
)

OUTPUT_PATH = Path("runtime/events/specialized_detections.jsonl")


TARGET_CLASSES = {
    "machinery",
    "vehicle",
}


def detect_specialized(video_path: str):
    model = YOLO(str(MODEL_PATH))

    cap = cv2.VideoCapture(video_path)

    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for frame_idx in range(frame_count):
            ok, frame = cap.read()

            if not ok:
                break

            timestamp = frame_idx / fps if fps > 0 else 0.0

            results = model(
                frame,
                device=0,
                conf=0.35,
                verbose=False,
            )

            for result in results:
                if result.boxes is None:
                    continue

                for box in result.boxes:
                    class_id = int(box.cls[0])
                    confidence = float(box.conf[0])
                    class_name = model.names[class_id]

                    if class_name not in TARGET_CLASSES:
                        continue

                    x1, y1, x2, y2 = map(
                        float,
                        box.xyxy[0].tolist()
                    )

                    record = {
                        "event_type": "specialized_detection",
                        "class_name": class_name,
                        "timestamp": round(timestamp, 3),
                        "confidence": round(confidence, 4),
                        "bbox": [
                            round(x1, 2),
                            round(y1, 2),
                            round(x2, 2),
                            round(y2, 2),
                        ],
                    }

                    import json
                    f.write(json.dumps(record) + "\n")

    cap.release()

    print("Specialized detection complete.")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--video",
        required=True,
        help="Path to video"
    )

    args = parser.parse_args()

    detect_specialized(args.video)