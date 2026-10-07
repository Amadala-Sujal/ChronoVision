import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def load_tracks(path):
    tracks = {}

    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            record = json.loads(line)
            track_id = int(record["track_id"])
            tracks.setdefault(track_id, []).append(record)

    for track_id in tracks:
        tracks[track_id].sort(
            key=lambda x: x["frame"]
        )

    return tracks


def load_zone(path):
    data = json.loads(
        Path(path).read_text(encoding="utf-8")
    )

    polygon = data.get("polygon")

    if not polygon or len(polygon) < 3:
        raise ValueError(
            "Zone must contain at least 3 polygon points."
        )

    return data


def get_zone_point(record):
    """
    For people, use the bottom-center of the bounding box.
    This is more meaningful for floor/ground zones than
    the geometric center of the box.

    For other objects, use the box center.
    """
    x1, y1, x2, y2 = record["bbox"]

    if record.get("class_name") == "person":
        return (
            (x1 + x2) / 2.0,
            y2,
        )

    return (
        (x1 + x2) / 2.0,
        (y1 + y2) / 2.0,
    )


def is_inside(point, polygon):
    contour = np.array(
        polygon,
        dtype=np.float32,
    )

    return (
        cv2.pointPolygonTest(
            contour,
            (
                float(point[0]),
                float(point[1]),
            ),
            False,
        ) >= 0
    )


def detect_zone_events(
    tracks,
    zone,
    fps,
):
    polygon = zone["polygon"]
    zone_name = zone.get(
        "name",
        "restricted_zone",
    )

    events = []

    # Prevent inside/outside flipping from tiny tracking noise.
    MIN_STATE_DURATION = 0.5
    MIN_EVENT_GAP = 0.8

    min_state_frames = max(
        1,
        int(fps * MIN_STATE_DURATION),
    )

    for track_id, records in tracks.items():
        if not records:
            continue

        raw_states = []

        for record in records:
            point = get_zone_point(record)

            inside = is_inside(
                point,
                polygon,
            )

            raw_states.append(
                {
                    "inside": inside,
                    "time_sec": record["time_sec"],
                    "confidence": record["confidence"],
                    "record": record,
                }
            )

        initial_state = raw_states[0]["inside"]

        # If the track begins inside the zone, we cannot claim
        # that the entry happened inside the observed video.
        current_state = initial_state

        if initial_state:
            first = raw_states[0]

            events.append(
                {
                    "event_type": "zone_present_at_start",
                    "track_id": track_id,
                    "class_name": first["record"]["class_name"],
                    "zone": zone_name,
                    "time_sec": round(
                        first["time_sec"],
                        3,
                    ),
                    "duration_sec": 0.0,
                    "confidence": first["confidence"],
                    "details": (
                        f"Track {track_id} was already "
                        f"inside zone '{zone_name}' "
                        f"when observation began."
                    ),
                }
            )

        candidate_state = None
        candidate_start = None
        candidate_frames = 0

        last_event_time = -9999.0

        for item in raw_states[1:]:
            observed_state = item["inside"]

            if observed_state == current_state:
                candidate_state = None
                candidate_start = None
                candidate_frames = 0
                continue

            if candidate_state != observed_state:
                candidate_state = observed_state
                candidate_start = item["time_sec"]
                candidate_frames = 1
            else:
                candidate_frames += 1

            if candidate_frames >= min_state_frames:
                old_state = current_state
                current_state = candidate_state

                event_type = (
                    "zone_entered"
                    if current_state
                    else "zone_exited"
                )

                event_time = candidate_start

                if (
                    event_time - last_event_time
                    >= MIN_EVENT_GAP
                ):
                    events.append(
                        {
                            "event_type": event_type,
                            "track_id": track_id,
                            "class_name": item["record"]["class_name"],
                            "zone": zone_name,
                            "time_sec": round(
                                event_time,
                                3,
                            ),
                            "duration_sec": 0.0,
                            "confidence": item["confidence"],
                            "details": (
                                f"Track {track_id} "
                                f"{'entered' if current_state else 'exited'} "
                                f"zone '{zone_name}'."
                            ),
                        }
                    )

                    last_event_time = event_time

                candidate_state = None
                candidate_start = None
                candidate_frames = 0

        # Create a useful occupancy duration when a real
        # entry is followed by an exit.
        track_zone_events = [
            e
            for e in events
            if e["track_id"] == track_id
            and e["zone"] == zone_name
        ]

        active_entry = None

        for event in track_zone_events:
            if event["event_type"] == "zone_entered":
                active_entry = event

            elif (
                event["event_type"] == "zone_exited"
                and active_entry is not None
            ):
                duration = (
                    event["time_sec"]
                    - active_entry["time_sec"]
                )

                events.append(
                    {
                        "event_type": "zone_occupancy",
                        "track_id": track_id,
                        "class_name": event["class_name"],
                        "zone": zone_name,
                        "time_sec": active_entry["time_sec"],
                        "duration_sec": round(
                            duration,
                            3,
                        ),
                        "confidence": min(
                            active_entry["confidence"],
                            event["confidence"],
                        ),
                        "details": (
                            f"Track {track_id} remained "
                            f"inside zone '{zone_name}' "
                            f"for {duration:.2f} seconds."
                        ),
                    }
                )

                active_entry = None

    events.sort(
        key=lambda x: x["time_sec"]
    )

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
        "--zone",
        required=True,
    )

    parser.add_argument(
        "--out-dir",
        default="runtime/events",
    )

    args = parser.parse_args()

    tracks_path = Path(args.tracks)
    summary_path = Path(args.summary)
    zone_path = Path(args.zone)
    out_dir = Path(args.out_dir)

    if not tracks_path.exists():
        raise FileNotFoundError(
            f"Track file not found: {tracks_path}"
        )

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Track summary not found: {summary_path}"
        )

    if not zone_path.exists():
        raise FileNotFoundError(
            f"Zone file not found: {zone_path}"
        )

    summary = json.loads(
        summary_path.read_text(
            encoding="utf-8"
        )
    )

    tracks = load_tracks(
        tracks_path
    )

    zone = load_zone(
        zone_path
    )

    events = detect_zone_events(
        tracks=tracks,
        zone=zone,
        fps=summary["fps"],
    )

    out_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output = (
        out_dir
        / "zone_events.jsonl"
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
        "=== ChronoVision Zone Engine v2 ==="
    )
    print(
        f"Zone: "
        f"{zone.get('name', 'unnamed')}"
    )
    print(
        f"Polygon points: "
        f"{len(zone['polygon'])}"
    )
    print(
        f"Zone events: {len(events)}"
    )

    for event in events:
        print(
            f"  {event['event_type']} | "
            f"Track {event['track_id']} | "
            f"{event['time_sec']:.3f}s"
            + (
                f" | duration "
                f"{event['duration_sec']:.3f}s"
                if event.get(
                    "duration_sec",
                    0.0
                ) > 0
                else ""
            )
        )

    print(
        f"Saved: {output}"
    )
    print(
        "STEP 7 ROBUST ZONE ENGINE COMPLETE"
    )


if __name__ == "__main__":
    main()