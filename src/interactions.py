import argparse
import json
import math
from collections import defaultdict, deque
from itertools import combinations
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


def center_distance(a, b):
    return math.sqrt(
        (a[0] - b[0]) ** 2
        + (a[1] - b[1]) ** 2
    )


def box_height(record):
    x1, y1, x2, y2 = record["bbox"]
    return max(1.0, y2 - y1)


def interaction_threshold(a, b):
    # Scales with the apparent size of both tracked objects.
    average_height = (
        box_height(a) + box_height(b)
    ) / 2.0

    return max(
        55.0,
        average_height * 0.55,
    )


def build_frame_index(tracks):
    frame_index = defaultdict(dict)

    for track_id, records in tracks.items():
        for record in records:
            frame_index[
                int(record["frame"])
            ][track_id] = record

    return frame_index


def detect_interactions(tracks, fps):
    frame_index = build_frame_index(tracks)

    # Require roughly half a second of sustained proximity.
    min_duration = 0.5

    # Prevent rapid event flickering.
    min_event_gap = 1.0

    pair_state = {}
    events = []

    for frame in sorted(frame_index):
        objects = frame_index[frame]
        time_sec = (
            next(iter(objects.values()))["time_sec"]
            if objects
            else frame / fps
        )

        for track_a, track_b in combinations(
            sorted(objects),
            2,
        ):
            a = objects[track_a]
            b = objects[track_b]

            distance = center_distance(
                a["center"],
                b["center"],
            )

            threshold = interaction_threshold(
                a,
                b,
            )

            close = distance <= threshold

            pair = (track_a, track_b)

            state = pair_state.setdefault(
                pair,
                {
                    "active": False,
                    "candidate_start": None,
                    "last_event": -9999.0,
                },
            )

            if close and not state["active"]:
                state["candidate_start"] = time_sec

                if (
                    time_sec
                    - state["last_event"]
                    >= min_event_gap
                ):
                    state["active"] = True

            elif close and state["active"]:
                duration = (
                    time_sec
                    - state["candidate_start"]
                )

                if duration >= min_duration:
                    # Only emit once when the interaction
                    # crosses the minimum duration.
                    if state.get(
                        "emitted",
                        False,
                    ) is False:
                        confidence = min(
                            float(a["confidence"]),
                            float(b["confidence"]),
                        )

                        events.append(
                            {
                                "event_type": "interaction_candidate",
                                "track_a": track_a,
                                "track_b": track_b,
                                "class_a": a["class_name"],
                                "class_b": b["class_name"],
                                "time_sec": round(
                                    state["candidate_start"],
                                    3,
                                ),
                                "duration_sec": round(
                                    duration,
                                    3,
                                ),
                                "distance_px": round(
                                    distance,
                                    2,
                                ),
                                "confidence": round(
                                    confidence,
                                    4,
                                ),
                                "verification": "geometric_proximity",
                                "details": (
                                    f"Tracks {track_a} and "
                                    f"{track_b} remained "
                                    f"within interaction "
                                    f"distance."
                                ),
                            }
                        )

                        state["emitted"] = True

            else:
                if state["active"]:
                    end_time = time_sec

                    if state["candidate_start"] is not None:
                        duration = (
                            end_time
                            - state["candidate_start"]
                        )

                        if duration >= min_duration:
                            events.append(
                                {
                                    "event_type": "interaction_ended",
                                    "track_a": track_a,
                                    "track_b": track_b,
                                    "class_a": a["class_name"],
                                    "class_b": b["class_name"],
                                    "time_sec": round(
                                        end_time,
                                        3,
                                    ),
                                    "duration_sec": round(
                                        duration,
                                        3,
                                    ),
                                    "confidence": min(
                                        float(a["confidence"]),
                                        float(b["confidence"]),
                                    ),
                                    "verification": "geometric_proximity",
                                    "details": (
                                        f"Tracks {track_a} and "
                                        f"{track_b} separated "
                                        f"after a proximity "
                                        f"episode."
                                    ),
                                }
                            )

                    state["last_event"] = end_time

                state["active"] = False
                state["candidate_start"] = None
                state["emitted"] = False

    # Handle an interaction that continues to the final frame.
    last_frame = max(
        frame_index
    ) if frame_index else 0

    last_time = (
        last_frame / fps
        if fps
        else 0.0
    )

    for pair, state in pair_state.items():
        if (
            state["active"]
            and state["candidate_start"] is not None
            and not state.get("ended_written", False)
        ):
            duration = (
                last_time
                - state["candidate_start"]
            )

            if duration >= min_duration:
                events.append(
                    {
                        "event_type": "interaction_ended",
                        "track_a": pair[0],
                        "track_b": pair[1],
                        "time_sec": round(
                            last_time,
                            3,
                        ),
                        "duration_sec": round(
                            duration,
                            3,
                        ),
                        "confidence": 0.0,
                        "verification": "geometric_proximity",
                        "details": (
                            f"Interaction candidate "
                            f"continued to the end "
                            f"of the observed video."
                        ),
                    }
                )

    # Remove accidental duplicate interaction candidates.
    deduped = []
    seen = set()

    for event in sorted(
        events,
        key=lambda x: x["time_sec"],
    ):
        key = (
            event["event_type"],
            event.get("track_a"),
            event.get("track_b"),
            round(event["time_sec"], 1),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(event)

    return deduped


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
        summary_path.read_text(
            encoding="utf-8"
        )
    )

    tracks = load_tracks(
        tracks_path
    )

    events = detect_interactions(
        tracks=tracks,
        fps=summary["fps"],
    )

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        out_dir
        / "interaction_events.jsonl"
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
        "=== ChronoVision Interaction Engine ==="
    )
    print(
        f"Interaction events: {len(events)}"
    )

    for event in events:
        print(
            f"  {event['event_type']} | "
            f"Tracks "
            f"{event.get('track_a')} & "
            f"{event.get('track_b')} | "
            f"{event['time_sec']:.3f}s"
        )

    print(f"Saved: {output}")
    print("STEP 9 COMPLETE")


if __name__ == "__main__":
    main()