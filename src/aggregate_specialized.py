import json
from pathlib import Path


INPUT_PATH = Path("runtime/events/specialized_detections.jsonl")
OUTPUT_PATH = Path("runtime/events/specialized_events.jsonl")

MIN_CONFIDENCE = 0.50
MAX_GAP_SECONDS = 0.50


def load_detections():
    detections = []

    with INPUT_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            if item.get("confidence", 0.0) < MIN_CONFIDENCE:
                continue

            detections.append(item)

    return detections


def aggregate():
    detections = load_detections()

    grouped = {}

    for item in detections:
        class_name = item["class_name"]
        grouped.setdefault(class_name, []).append(item)

    events = []

    for class_name, items in grouped.items():
        items.sort(key=lambda x: x["timestamp"])

        start_time = items[0]["timestamp"]
        last_time = items[0]["timestamp"]

        max_confidence = items[0]["confidence"]
        count = 1

        for item in items[1:]:
            timestamp = item["timestamp"]

            if timestamp - last_time <= MAX_GAP_SECONDS:
                last_time = timestamp
                max_confidence = max(
                    max_confidence,
                    item["confidence"]
                )
                count += 1
            else:
                events.append({
                    "event_type": "specialized_object_present",
                    "class_name": class_name,
                    "start_timestamp": round(start_time, 3),
                    "end_timestamp": round(last_time, 3),
                    "duration_sec": round(
                        last_time - start_time, 3
                    ),
                    "max_confidence": round(
                        max_confidence, 4
                    ),
                    "detection_count": count,
                })

                start_time = timestamp
                last_time = timestamp
                max_confidence = item["confidence"]
                count = 1

        events.append({
            "event_type": "specialized_object_present",
            "class_name": class_name,
            "start_timestamp": round(start_time, 3),
            "end_timestamp": round(last_time, 3),
            "duration_sec": round(
                last_time - start_time, 3
            ),
            "max_confidence": round(
                max_confidence, 4
            ),
            "detection_count": count,
        })

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_PATH.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    print("Specialized event aggregation complete.")
    print(f"Input detections: {len(detections)}")
    print(f"Aggregated events: {len(events)}")
    print(f"Output: {OUTPUT_PATH}")


if __name__ == "__main__":
    aggregate()