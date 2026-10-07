import argparse
import json
from pathlib import Path

import cv2
import torch
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", default="runtime/tracks")
    parser.add_argument("--model", default="yolo26n.pt")
    parser.add_argument("--tracker", default="botsort.yaml")
    parser.add_argument("--device", default="0")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    args = parser.parse_args()

    video_path = Path(args.video)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    duration = frame_count / fps if fps else 0.0

    print("=== ChronoVision Tracking ===")
    print(f"Video: {video_path}")
    print(f"Resolution: {width}x{height}")
    print(f"FPS: {fps:.2f}")
    print(f"Frames: {frame_count}")
    print(f"Duration: {duration:.2f}s")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"Requested device: {args.device}")

    model = YOLO(args.model)

    tracks_file = out_dir / "tracks.jsonl"
    summary_file = out_dir / "track_summary.json"

    frames_processed = 0
    total_detections = 0
    unique_track_ids = set()
    class_counts = {}

    with tracks_file.open("w", encoding="utf-8") as f:
        results = model.track(
            source=str(video_path),
            tracker=args.tracker,
            device=args.device,
            imgsz=args.imgsz,
            conf=args.conf,
            stream=True,
            verbose=False,
        )

        for result in results:
            frames_processed += 1

            if result.boxes is None or len(result.boxes) == 0:
                continue

            ids = result.boxes.id
            classes = result.boxes.cls
            confidences = result.boxes.conf
            boxes = result.boxes.xyxy

            if ids is None:
                continue

            ids_list = ids.int().cpu().tolist()
            classes_list = classes.int().cpu().tolist()
            conf_list = confidences.cpu().tolist()
            boxes_list = boxes.cpu().tolist()

            time_sec = (frames_processed - 1) / fps

            for track_id, class_id, confidence, box in zip(
                ids_list, classes_list, conf_list, boxes_list
            ):
                x1, y1, x2, y2 = box

                cx = (x1 + x2) / 2.0
                cy = (y1 + y2) / 2.0

                class_name = model.names.get(
                    int(class_id), str(class_id)
                )

                record = {
                    "frame": frames_processed - 1,
                    "time_sec": round(time_sec, 3),
                    "track_id": int(track_id),
                    "class_id": int(class_id),
                    "class_name": class_name,
                    "confidence": round(float(confidence), 4),
                    "bbox": [
                        round(float(x1), 2),
                        round(float(y1), 2),
                        round(float(x2), 2),
                        round(float(y2), 2),
                    ],
                    "center": [
                        round(cx, 2),
                        round(cy, 2),
                    ],
                }

                f.write(json.dumps(record) + "\n")

                unique_track_ids.add(int(track_id))
                total_detections += 1
                class_counts[class_name] = class_counts.get(class_name, 0) + 1

    summary = {
        "video": str(video_path),
        "fps": fps,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "duration_sec": round(duration, 3),
        "frames_processed": frames_processed,
        "total_detections": total_detections,
        "unique_track_ids": sorted(unique_track_ids),
        "unique_track_count": len(unique_track_ids),
        "class_counts": class_counts,
        "device_requested": args.device,
        "cuda_available": torch.cuda.is_available(),
        "tracker": args.tracker,
        "model": args.model,
    }

    summary_file.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print()
    print("Tracking complete.")
    print(f"Frames processed: {frames_processed}")
    print(f"Total tracked detections: {total_detections}")
    print(f"Unique track IDs: {len(unique_track_ids)}")
    print(f"Track IDs: {sorted(unique_track_ids)}")
    print(f"Track data: {tracks_file}")
    print(f"Summary: {summary_file}")
    print("STEP 2 COMPLETE")


if __name__ == "__main__":
    main()