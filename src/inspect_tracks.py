import json
from collections import defaultdict

path = "runtime/tracks/tracks.jsonl"

tracks = defaultdict(list)

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue

        record = json.loads(line)
        tracks[int(record["track_id"])].append(record)

print("=== TRACK INSPECTION ===")

for track_id in sorted(tracks):
    records = tracks[track_id]

    start = records[0]["time_sec"]
    end = records[-1]["time_sec"]
    duration = end - start

    print(
        f"Track {track_id}: "
        f"frames={len(records)}, "
        f"start={start:.3f}s, "
        f"end={end:.3f}s, "
        f"duration={duration:.3f}s"
    )

print()
print("TRACK INSPECTION COMPLETE")