import json
from pathlib import Path


EVENTS_PATH = Path("runtime/events/specialized_events.jsonl")


def load_events():
    events = []

    if not EVENTS_PATH.exists():
        return events

    with EVENTS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                events.append(json.loads(line))

    return events


def query_machinery():
    events = load_events()

    machinery_events = [
        event
        for event in events
        if event.get("class_name") == "machinery"
    ]

    if not machinery_events:
        return {
            "status": "no_match",
            "answer": "No machinery was detected."
        }

    first = machinery_events[0]

    start = first["start_timestamp"]
    end = first["end_timestamp"]
    duration = first["duration_sec"]
    confidence = first["max_confidence"]

    return {
        "status": "answer",
        "answer": (
            f"Machinery was detected from "
            f"{start:.3f}s to {end:.3f}s "
            f"for {duration:.3f} seconds."
        ),
        "timestamp": start,
        "end_timestamp": end,
        "duration_seconds": duration,
        "confidence": confidence,
    }


if __name__ == "__main__":
    result = query_machinery()

    print(json.dumps(result, indent=2))
