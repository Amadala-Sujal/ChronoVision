import argparse
import json
import re
from pathlib import Path


EVENT_ALIASES = {
    "movement stopped": "movement_stopped",
    "movement stop": "movement_stopped",
    "stopped moving": "movement_stopped",
    "stop": "movement_stopped",
    "stopped": "movement_stopped",
    "zone entered": "zone_entered",
    "entered zone": "zone_entered",
    "zone entry": "zone_entered",
    "zone exited": "zone_exited",
    "exited zone": "zone_exited",
    "zone exit": "zone_exited",
    "movement started": "movement_started",
    "movement start": "movement_started",
    "started moving": "movement_started",
    "start": "movement_started",
    "started": "movement_started",
    "interaction": "interaction_candidate",
    "interaction candidate": "interaction_candidate",
    "interaction ended": "interaction_ended",
    "proximity": "interaction_candidate",
    "stationary": "stationary_interval",
    "still": "stationary_interval",

    "appeared": "track_started",
    "track started": "track_started",

    "last seen": "track_last_seen",
}

BOOKKEEPING_EVENTS = {
    "track_started",
    "track_last_seen",
}


def load_events(path):
    events = []

    with Path(path).open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if line:
                events.append(json.loads(line))

    events.sort(key=lambda x: x["time_sec"])
    return events


def detect_event_type(query):
    q = query.lower()

    for phrase in sorted(EVENT_ALIASES, key=len, reverse=True):
        if phrase in q:
            return EVENT_ALIASES[phrase]

    return None


def detect_relation(query):
    q = query.lower()

    if "immediately before" in q:
        return "IMMEDIATELY_BEFORE"

    if "immediately after" in q:
        return "IMMEDIATELY_AFTER"

    if "before" in q:
        return "BEFORE"

    if "after" in q:
        return "AFTER"

    return None


def detect_track_id(query):
    match = re.search(
        r"(?:track|person|object|id)\s*#?\s*(\d+)",
        query.lower(),
    )

    return int(match.group(1)) if match else None


def wants_all_events(query):
    q = query.lower()

    return any(
        phrase in q
        for phrase in [
            "all events",
            "all the events",
            "every event",
            "everything",
            "events that happened",
            "what events",
        ]
    )


def matching_events(events, event_type=None, track_id=None, include_bookkeeping=False):
    matches = []

    for event in events:
        if not include_bookkeeping:
            if event["event_type"] in BOOKKEEPING_EVENTS:
                continue

        if event_type and event["event_type"] != event_type:
            continue

        if track_id is not None and event.get("track_id") != track_id:
            continue

        matches.append(event)

    return matches


def format_event(event):
    timestamp = float(event["time_sec"])
    duration = float(event.get("duration_sec", 0.0))

    event_type = event["event_type"]

    if event_type in {
        "interaction_candidate",
        "interaction_ended",
    }:
        description = event.get(
            "details",
            f"Interaction between tracks "
            f"{event.get('track_a')} and "
            f"{event.get('track_b')}.",
        )

        return {
            "event_type": event_type,
            "track_a": event.get("track_a"),
            "track_b": event.get("track_b"),
            "class_a": event.get("class_a"),
            "class_b": event.get("class_b"),
            "timestamp_sec": round(timestamp, 3),
            "duration_sec": round(duration, 3),
            "confidence": round(
                float(event.get("confidence", 0.0)),
                4,
            ),
            "verification": event.get(
                "verification",
                "unknown",
            ),
            "description": description,
            "evidence_start_sec": round(
                max(0.0, timestamp - 2.0),
                3,
            ),
            "evidence_end_sec": round(
                timestamp + max(2.0, duration + 1.0),
                3,
            ),
        }

    if event_type == "stationary_interval":
        evidence_start = max(
            0.0,
            timestamp - 1.0,
        )
        evidence_end = (
            timestamp
            + duration
            + 1.0
        )
    else:
        evidence_start = max(
            0.0,
            timestamp - 2.0,
        )
        evidence_end = timestamp + 2.0

    return {
        "event_type": event_type,
        "track_id": event.get("track_id"),
        "class_name": event.get(
            "class_name",
            "unknown",
        ),
        "timestamp_sec": round(
            timestamp,
            3,
        ),
        "duration_sec": round(
            duration,
            3,
        ),
        "confidence": round(
            float(event.get("confidence", 0.0)),
            4,
        ),
        "description": event.get(
            "details",
            "",
        ),
        "evidence_start_sec": round(
            evidence_start,
            3,
        ),
        "evidence_end_sec": round(
            evidence_end,
            3,
        ),
    }

def related_events(events, target, relation, return_all=False):
    target_time = target["time_sec"]

    candidates = []

    for event in events:
        if event is target:
            continue

        if event["event_type"] in BOOKKEEPING_EVENTS:
            continue

        event_time = event["time_sec"]

        if relation in ("BEFORE", "IMMEDIATELY_BEFORE"):
            if event_time < target_time:
                candidates.append(event)

        elif relation in ("AFTER", "IMMEDIATELY_AFTER"):
            if event_time > target_time:
                candidates.append(event)

    if not candidates:
        return []

    if relation in ("BEFORE", "IMMEDIATELY_BEFORE"):
        candidates.sort(
            key=lambda e: target_time - e["time_sec"]
        )
    else:
        candidates.sort(
            key=lambda e: e["time_sec"] - target_time
        )

    if return_all or relation.startswith("IMMEDIATELY_") is False and False:
        return candidates

    return candidates[:1]


def answer_query(query, events):
    q = query.lower().strip()

    event_type = detect_event_type(q)
    relation = detect_relation(q)
    track_id = detect_track_id(q)
    include_bookkeeping = (
        "appeared" in q
        or "last seen" in q
        or "track started" in q
    )

    candidates = matching_events(
        events,
        event_type=event_type,
        track_id=track_id,
        include_bookkeeping=include_bookkeeping,
    )

    # COUNT
    if any(
        word in q
        for word in ["how many", "count", "number of", "times"]
    ):
        return {
            "query": query,
            "answer_type": "COUNT",
            "answer": f"{len(candidates)} matching event(s) found.",
            "count": len(candidates),
            "events": [
                format_event(e)
                for e in candidates
            ],
            "status": "success" if candidates else "no_match",
        }

    # DURATION
    if any(
        word in q
        for word in ["how long", "duration", "longest"]
    ):
        duration_events = [
            e for e in candidates
            if e.get("duration_sec", 0.0) > 0
        ]

        if not duration_events:
            return {
                "query": query,
                "answer_type": "DURATION",
                "answer": "No measurable duration event found.",
                "status": "no_match",
            }

        if "longest" in q:
            target = max(
                duration_events,
                key=lambda e: e["duration_sec"],
            )
        else:
            target = duration_events[0]

        result = format_event(target)

        return {
            "query": query,
            "answer_type": "DURATION",
            "answer": (
                f"Duration was "
                f"{result['duration_sec']:.2f} seconds."
            ),
            "timestamp_sec": result["timestamp_sec"],
            "duration_sec": result["duration_sec"],
            "evidence": result,
            "status": "success",
        }

    # TEMPORAL
    if relation and candidates:
        all_requested = wants_all_events(q)

        answers = []

        for target in candidates:
            related = related_events(
                events,
                target,
                relation,
                return_all=all_requested,
            )

            if related:
                answers.append(
                    {
                        "target_event": format_event(target),
                        "related_events": [
                            format_event(e)
                            for e in related
                        ],
                    }
                )

        if not answers:
            return {
                "query": query,
                "answer_type": "TEMPORAL",
                "relation": relation,
                "answer": "No related event found.",
                "status": "no_match",
            }

        return {
            "query": query,
            "answer_type": "TEMPORAL",
            "relation": relation,
            "answers": answers,
            "status": "success",
        }

    # DEFAULT EVENT LIST
    if candidates:
        return {
            "query": query,
            "answer_type": "EVENT_LIST",
            "answer": f"{len(candidates)} matching event(s) found.",
            "events": [
                format_event(e)
                for e in candidates
            ],
            "status": "success",
        }

    return {
        "query": query,
        "answer_type": "UNKNOWN",
        "answer": "No matching event was found.",
        "status": "no_match",
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--events",
        default="runtime/events/events.jsonl",
    )

    parser.add_argument(
        "--query",
        required=True,
    )

    args = parser.parse_args()

    events_path = Path(args.events)

    if not events_path.exists():
        raise FileNotFoundError(
            f"Event file not found: {events_path}"
        )

    events = load_events(events_path)

    result = answer_query(
        args.query,
        events,
    )

    print(json.dumps(result, indent=2))

    if result.get("status") == "success":
        print("STEP 6 REASONING V2 COMPLETE")
    else:
        print("STEP 6 QUERY: NO MATCH")


if __name__ == "__main__":
    main()
 