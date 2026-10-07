import argparse
import json
from pathlib import Path


def load_jsonl(path):
    path = Path(path)

    if not path.exists():
        return []

    events = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                events.append(json.loads(line))

    return events


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--base",
        default="runtime/events/events.jsonl",
    )

    parser.add_argument(
        "--zone",
        default="runtime/events/zone_events.jsonl",
    )

    parser.add_argument(
        "--interaction",
        default="runtime/events/interaction_events.jsonl",
    )

    parser.add_argument(
        "--output",
        default="runtime/events/all_events.jsonl",
    )

    args = parser.parse_args()

    sources = [
        args.base,
        args.zone,
        args.interaction,
    ]

    all_events = []

    for source in sources:
        events = load_jsonl(source)
        print(
            f"{source}: {len(events)} event(s)"
        )
        all_events.extend(events)

    # Exact duplicate protection.
    seen = set()
    unique_events = []

    for event in all_events:
        key = (
            event.get("event_type"),
            event.get("track_id"),
            event.get("track_a"),
            event.get("track_b"),
            event.get("time_sec"),
            event.get("zone"),
        )

        if key in seen:
            continue

        seen.add(key)
        unique_events.append(event)

    unique_events.sort(
        key=lambda x: x.get("time_sec", 0.0)
    )

    output = Path(args.output)
    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as f:
        for event in unique_events:
            f.write(
                json.dumps(event)
                + "\n"
            )

    print()
    print(
        "=== ChronoVision Unified Event Store v2 ==="
    )
    print(
        f"Unified events: {len(unique_events)}"
    )
    print(
        f"Saved: {output}"
    )
    print("STEP 10 MERGE COMPLETE")


if __name__ == "__main__":
    main()