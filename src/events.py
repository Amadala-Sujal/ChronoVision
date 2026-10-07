import argparse
import json
import math
from collections import defaultdict, deque
from pathlib import Path


def distance(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2)


def load_tracks(path):
    tracks = defaultdict(list)

    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                record = json.loads(line)
                tracks[int(record["track_id"])].append(record)

    for track_id in tracks:
        tracks[track_id].sort(key=lambda x: x["frame"])

    return tracks


def detect_events(tracks, fps, width, height):
    events = []

    # Movement thresholds in pixels per frame.
    MOVING_THRESHOLD = 4.0
    STATIONARY_THRESHOLD = 2.0

    # Smooth movement over this many frames.
    SMOOTHING_FRAMES = 8

    # A new state must persist this long before we accept it.
    MIN_STATE_DURATION = 0.7

    # Prevent duplicate events very close together.
    MIN_EVENT_GAP = 1.5

    min_state_frames = max(1, int(fps * MIN_STATE_DURATION))

    for track_id, records in tracks.items():
        if not records:
            continue

        class_name = records[0]["class_name"]

        events.append(
            {
                "event_type": "track_started",
                "track_id": track_id,
                "class_name": class_name,
                "time_sec": round(records[0]["time_sec"], 3),
                "duration_sec": 0.0,
                "confidence": records[0]["confidence"],
                "details": "Track first observed in the video.",
            }
        )

        movement_window = deque(maxlen=SMOOTHING_FRAMES)

        previous_center = None
        raw_states = []

        for record in records:
            center = record["center"]

            if previous_center is None:
                movement = 0.0
            else:
                movement = distance(previous_center, center)

            previous_center = center
            movement_window.append(movement)

            avg_movement = sum(movement_window) / len(movement_window)

            if avg_movement >= MOVING_THRESHOLD:
                raw_state = "moving"
            elif avg_movement <= STATIONARY_THRESHOLD:
                raw_state = "stationary"
            else:
                raw_state = (
                    raw_states[-1][0]
                    if raw_states
                    else "stationary"
                )

            raw_states.append(
                (
                    raw_state,
                    record["time_sec"],
                    record["confidence"],
                )
            )

        # Confirm state changes only after sustained stability.
        committed_state = raw_states[0][0]

        candidate_state = None
        candidate_start = None
        candidate_frames = 0

        confirmed_states = []

        for state, time_sec, confidence in raw_states:

            if state == committed_state:
                candidate_state = None
                candidate_start = None
                candidate_frames = 0

            else:
                if candidate_state != state:
                    candidate_state = state
                    candidate_start = time_sec
                    candidate_frames = 1
                else:
                    candidate_frames += 1

                if candidate_frames >= min_state_frames:
                    committed_state = candidate_state

                    confirmed_states.append(
                        {
                            "state": committed_state,
                            "time_sec": candidate_start,
                            "confidence": confidence,
                        }
                    )

                    candidate_state = None
                    candidate_start = None
                    candidate_frames = 0

        # Build transition events.
        last_event_time = {
            "movement_started": -9999.0,
            "movement_stopped": -9999.0,
        }

        for transition in confirmed_states:
            state = transition["state"]
            time_sec = transition["time_sec"]
            confidence = transition["confidence"]

            if state == "moving":
                event_type = "movement_started"
                details = (
                    f"Track {track_id} transitioned "
                    f"from stationary to moving."
                )
            else:
                event_type = "movement_stopped"
                details = (
                    f"Track {track_id} transitioned "
                    f"from moving to stationary."
                )

            if (
                time_sec - last_event_time[event_type]
                >= MIN_EVENT_GAP
            ):
                events.append(
                    {
                        "event_type": event_type,
                        "track_id": track_id,
                        "class_name": class_name,
                        "time_sec": round(time_sec, 3),
                        "duration_sec": 0.0,
                        "confidence": confidence,
                        "details": details,
                    }
                )

                last_event_time[event_type] = time_sec

        # Build stationary intervals from confirmed states.
        stationary_start = None
        previous_confirmed_state = None

        for transition in confirmed_states:
            state = transition["state"]
            time_sec = transition["time_sec"]

            if (
                state == "stationary"
                and previous_confirmed_state != "stationary"
            ):
                stationary_start = time_sec

            elif (
                state == "moving"
                and previous_confirmed_state == "stationary"
                and stationary_start is not None
            ):
                duration = time_sec - stationary_start

                if duration >= 2.0:
                    events.append(
                        {
                            "event_type": "stationary_interval",
                            "track_id": track_id,
                            "class_name": class_name,
                            "time_sec": round(stationary_start, 3),
                            "duration_sec": round(duration, 3),
                            "confidence": transition["confidence"],
                            "details": (
                                f"Track remained approximately "
                                f"stationary for {duration:.2f} seconds."
                            ),
                        }
                    )

                stationary_start = None

            previous_confirmed_state = state

        # Handle a stationary period continuing to the end.
        if stationary_start is not None:
            end_time = records[-1]["time_sec"]
            duration = end_time - stationary_start

            if duration >= 2.0:
                events.append(
                    {
                        "event_type": "stationary_interval",
                        "track_id": track_id,
                        "class_name": class_name,
                        "time_sec": round(stationary_start, 3),
                        "duration_sec": round(duration, 3),
                        "confidence": records[-1]["confidence"],
                        "details": (
                            f"Track remained approximately stationary "
                            f"for {duration:.2f} seconds."
                        ),
                    }
                )

        events.append(
            {
                "event_type": "track_last_seen",
                "track_id": track_id,
                "class_name": class_name,
                "time_sec": round(records[-1]["time_sec"], 3),
                "duration_sec": round(
                    records[-1]["time_sec"] - records[0]["time_sec"],
                    3,
                ),
                "confidence": records[-1]["confidence"],
                "details": "Last observed timestamp for this track.",
            }
        )

    events.sort(key=lambda x: x["time_sec"])

    return events


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tracks",
        default="runtime/tracks/tracks.jsonl",
    )

    parser.add_argument(
        "--summary",
        default="runtime/tracks/track_summary.json",
    )

    parser.add_argument(
        "--out-dir",
        default="runtime/events",
    )

    args = parser.parse_args()

    tracks_path = Path(args.tracks)
    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)

    if not tracks_path.exists():
        raise FileNotFoundError(
            f"Track file not found: {tracks_path}"
        )

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Track summary not found: {summary_path}"
        )

    summary = json.loads(
        summary_path.read_text(encoding="utf-8")
    )

    tracks = load_tracks(tracks_path)

    events = detect_events(
        tracks=tracks,
        fps=summary["fps"],
        width=summary["width"],
        height=summary["height"],
    )

    out_dir.mkdir(parents=True, exist_ok=True)

    events_file = out_dir / "events.jsonl"
    summary_file = out_dir / "event_summary.json"

    with events_file.open("w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    event_counts = defaultdict(int)

    for event in events:
        event_counts[event["event_type"]] += 1

    event_summary = {
        "source_tracks": str(tracks_path),
        "event_count": len(events),
        "event_counts": dict(event_counts),
        "events": events,
    }

    summary_file.write_text(
        json.dumps(event_summary, indent=2),
        encoding="utf-8",
    )

    print("=== ChronoVision Event Engine v2 ===")
    print(f"Tracks loaded: {len(tracks)}")
    print(f"Events generated: {len(events)}")
    print()
    print("Event counts:")

    for event_type, count in sorted(event_counts.items()):
        print(f"  {event_type}: {count}")

    print()
    print(f"Event data: {events_file}")
    print(f"Event summary: {summary_file}")
    print("STEP 3 ROBUST EVENT ENGINE COMPLETE")


if __name__ == "__main__":
    main()

