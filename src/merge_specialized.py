import json
from pathlib import Path

BASE_EVENTS = Path("runtime/events/all_events.jsonl")
SPECIALIZED_EVENTS = Path("runtime/events/specialized_events.jsonl")
OUTPUT_EVENTS = Path("runtime/events/all_events_with_specialized.jsonl")


def load_jsonl(path):
    events = []

    if not path.exists():
        return events

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    return events


base = load_jsonl(BASE_EVENTS)
specialized = load_jsonl(SPECIALIZED_EVENTS)

combined = base + specialized

combined.sort(
    key=lambda event: (
        event.get("time_sec",
        event.get("timestamp",
        event.get("start_timestamp", 0.0)))
    )
)

with OUTPUT_EVENTS.open("w", encoding="utf-8") as f:
    for event in combined:
        f.write(json.dumps(event) + "\n")

print("Specialized events merged.")
print(f"Base events: {len(base)}")
print(f"Specialized events: {len(specialized)}")
print(f"Combined events: {len(combined)}")
print(f"Output: {OUTPUT_EVENTS}")