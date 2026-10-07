import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def load_tracks(path):
    tracks = defaultdict(list)

    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                record = json.loads(line)
                tracks[int(record["track_id"])].append(record)

    for track_id in tracks:
        tracks[track_id].sort(
            key=lambda x: x["frame"]
        )

    return tracks


def distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
    )


def detect_untouched(
    tracks,
    min_duration,
    movement_threshold,
):
    events = []

    for track_id, records in tracks.items():

        if len(records) < 2:
            continue

        start_index = 0

        for index in range(1, len(records)):

            start = records[start_index]
            current = records[index]

            elapsed = (
                current["time_sec"]
                - start["time_sec"]
            )

            movement = distance(
                start["center"],
                current["center"],
            )

            if movement > movement_threshold:
                # Start a new stationary episode.
                start_index = index
                continue

            if elapsed >= min_duration:
                events.append(
                    {
                        "event_type":
                            "untouched_candidate",
                        "track_id":
                            track_id,
                        "class_name":
                            current["class_name"],
                        "time_sec":
                            round(
                                start["time_sec"],
                                3,
                            ),
                        "end_time_sec":
                            round(
                                current["time_sec"],
                                3,
                            ),
                        "duration_sec":
                            round(
                                elapsed,
                                3,
                            ),
                        "movement_px":
                            round(
                                movement,
                                2,
                            ),
                        "confidence":
                            round(
                                float(
                                    min(
                                        start["confidence"],
                                        current["confidence"],
                                    )
                                ),
                                4,
                            ),
                        "verification":
                            "low_motion_track",
                        "details":
                            (
                                f"Track {track_id} "
                                f"remained approximately "
                                f"stationary for "
                                f"{elapsed:.2f} seconds."
                            ),
                    }
                )

                # Don't emit this every frame.
                # Continue looking for a longer episode.
                break

    return events


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--tracks",
        default="runtime/tracks/tracks.jsonl",
    )

    parser.add_argument(
        "--min-duration",
        type=float,
        default=120.0,
    )

    parser.add_argument(
        "--movement-threshold",
        type=float,
        default=25.0,
    )

    parser.add_argument(
        "--out-dir",
        default="runtime/events",
    )

    args = parser.parse_args()

    tracks_path = Path(args.tracks)

    if not tracks_path.exists():
        raise FileNotFoundError(
            f"Track file not found: {tracks_path}"
        )

    tracks = load_tracks(
        tracks_path
    )

    events = detect_untouched(
        tracks=tracks,
        min_duration=args.min_duration,
        movement_threshold=args.movement_threshold,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        out_dir
        / "untouched_events.jsonl"
    )

    with output.open(
        "w",
        encoding="utf-8",
    ) as f:
        for event in events:
            f.write(
                json.dumps(event)
                + "\n"
            )

    print(
        "=== ChronoVision Untouched Object Engine ==="
    )
    print(
        f"Minimum duration: "
        f"{args.min_duration:.1f}s"
    )
    print(
        f"Movement threshold: "
        f"{args.movement_threshold:.1f}px"
    )
    print(
        f"Untouched candidates: "
        f"{len(events)}"
    )

    for event in events:
        print(
            f"  Track {event['track_id']} | "
            f"{event['duration_sec']:.2f}s"
        )

    print(
        f"Saved: {output}"
    )
    print(
        "STEP 13 COMPLETE"
    )


if __name__ == "__main__":
    main()