import json
import argparse
from pathlib import Path


EVENT_DIR = Path("runtime/events")


# ============================================================
# LOAD EVENTS
# ============================================================

def load_jsonl(path):
    events = []

    if not path.exists():
        return events

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    return events


def load_events():
    """
    Load the unified ChronoVision event graph and Gemini
    semantic events.
    """

    events = load_jsonl(
        EVENT_DIR / "all_events.jsonl"
    )

    semantic_events = load_jsonl(
        EVENT_DIR / "semantic_events.jsonl"
    )

    existing_keys = {
        (
            e.get("event_type"),
            round(timestamp(e), 2),
            e.get("track_id"),
        )
        for e in events
    }

    for event in semantic_events:

        key = (
            event.get("event_type"),
            round(timestamp(event), 2),
            event.get("track_id"),
        )

        if key not in existing_keys:
            events.append(event)

    events.sort(
        key=timestamp
    )

    return events


# ============================================================
# FIELD HELPERS
# ============================================================

def timestamp(event):
    """
    ChronoVision supports:
      - local CV: time_sec
      - semantic Gemini: timestamp
      - interval events: start_timestamp
    """

    value = event.get("time_sec")

    if value is not None:
        return float(value)

    value = event.get("timestamp")

    if value is not None:
        return float(value)

    value = event.get("start_timestamp")

    if value is not None:
        return float(value)

    return 0.0


def event_duration(event):
    """
    ChronoVision supports:
      - local CV: duration_sec
      - semantic events: duration / end_timestamp
    """

    value = event.get("duration_sec")

    if value is not None:
        try:
            return float(value)
        except Exception:
            pass

    value = event.get("duration")

    if value is not None:
        try:
            return float(value)
        except Exception:
            pass

    start = event.get(
        "time_sec",
        event.get(
            "timestamp",
            event.get(
                "start_timestamp"
            )
        )
    )

    end = event.get(
        "end_timestamp",
        event.get("end")
    )

    if start is not None and end is not None:
        try:
            return (
                float(end)
                - float(start)
            )
        except Exception:
            pass

    return None


def format_time(seconds):

    if seconds is None:
        return "unknown"

    return f"{float(seconds):.3f}s"


def event_label(event):

    event_type = event.get(
        "event_type",
        "event"
    )

    if event_type == "movement_started":

        track = event.get(
            "track_id",
            "unknown"
        )

        return (
            f"Track {track} started moving"
        )

    if event_type == "movement_stopped":

        track = event.get(
            "track_id",
            "unknown"
        )

        return (
            f"Track {track} stopped moving"
        )

    if event_type == "stationary_interval":

        track = event.get(
            "track_id",
            "unknown"
        )

        return (
            f"Track {track} became stationary"
        )

    if event_type == "zone_entered":

        track = event.get(
            "track_id",
            event.get(
                "person_id",
                "unknown"
            )
        )

        zone = event.get(
            "zone_name",
            event.get(
                "zone",
                "restricted area"
            )
        )

        return (
            f"Track {track} entered {zone}"
        )

    if event_type == "zone_exited":

        track = event.get(
            "track_id",
            "unknown"
        )

        zone = event.get(
            "zone_name",
            event.get(
                "zone",
                "zone"
            )
        )

        return (
            f"Track {track} exited {zone}"
        )

    if event_type == "interaction_candidate":

        a = event.get(
            "track_a",
            "unknown"
        )

        b = event.get(
            "track_b",
            "unknown"
        )

        return (
            f"Tracks {a} and {b} came into "
            f"interaction range"
        )

    if event_type == "interaction_ended":

        a = event.get(
            "track_a",
            "unknown"
        )

        b = event.get(
            "track_b",
            "unknown"
        )

        return (
            f"Interaction between tracks "
            f"{a} and {b} ended"
        )

    if event_type == "truck_arrived":

        return event.get(
            "description",
            event.get(
                "details",
                "Truck arrived"
            )
        )

    if event_type == "machine_unexpected_stop":

        return event.get(
            "description",
            event.get(
                "details",
                "Machine stopped unexpectedly"
            )
        )

    if event_type == "safety_alarm":

        return event.get(
            "description",
            event.get(
                "details",
                "Safety alarm occurred"
            )
        )

    if event_type == "object_untouched":

        return event.get(
            "description",
            event.get(
                "details",
                "Object remained untouched"
            )
        )

    return event.get(
        "description",
        event.get(
            "details",
            event_type.replace(
                "_",
                " "
            )
        )
    )


def meaningful_events(events):

    return [
        e for e in events
        if e.get("event_type") not in {
            "track_started",
            "track_last_seen",
            "zone_present_at_start"
        }
    ]


# ============================================================
# QUESTION CLASSIFICATION
# ============================================================

def classify_question(question):

    q = question.lower().strip()

    if (
        "restricted area" in q
        and "truck" in q
        and "after" in q
    ):
        return "restricted_area"

    if (
        "machine" in q
        and (
            "stop" in q
            or "stopped" in q
        )
    ):
        return "machine_stop"

    if (
        "safety alarm" in q
        and "before" in q
    ):
        return "before_alarm"

    if (
        "untouched" in q
        or (
            "object" in q
            and "2 minute" in q
        )
    ):
        return "untouched"

    if (
        "movement stopped" in q
        or "movement stop" in q
    ):
        return "before_movement_stop"

    if (
        "movement started" in q
        or "movement start" in q
    ):
        return "after_movement_start"

    if (
        "how long" in q
        and "stationary" in q
    ):
        return "stationary_duration"

    if (
        "how many" in q
        and "interaction" in q
    ):
        return "interaction_count"

    return "unsupported"


# ============================================================
# RESTRICTED AREA AFTER TRUCK
# ============================================================

def answer_restricted_area(events):

    trucks = [
        e for e in events
        if e.get("event_type")
        == "truck_arrived"
    ]

    entries = [
        e for e in events
        if e.get("event_type")
        == "zone_entered"
    ]

    if not trucks:

        return {
            "status": "insufficient_evidence",
            "answer": (
                "No truck-arrival event was detected."
            ),
            "timestamp": None
        }

    if not entries:

        return {
            "status": "no_match",
            "answer": (
                "No restricted-area entry was detected."
            ),
            "timestamp": None
        }

    truck = min(
        trucks,
        key=timestamp
    )

    matches = [
        e for e in entries
        if timestamp(e) > timestamp(truck)
    ]

    if not matches:

        return {
            "status": "no_match",
            "answer": (
                "No person entered the restricted "
                "area after the truck arrived."
            ),
            "timestamp": None
        }

    results = []

    for entry in matches:

        track = entry.get(
            "track_id",
            entry.get(
                "person_id",
                "unknown"
            )
        )

        results.append({
            "person_or_track": track,
            "entry_timestamp": timestamp(entry),
            "truck_timestamp": timestamp(truck),
            "gap_seconds": (
                timestamp(entry)
                - timestamp(truck)
            ),
            "description": event_label(entry)
        })

    return {
        "status": "answer",
        "answer": (
            f"{len(results)} person/track entry "
            f"event(s) occurred after the truck arrived."
        ),
        "timestamp": results[0]["entry_timestamp"],
        "truck_timestamp": timestamp(truck),
        "results": results
    }


# ============================================================
# MACHINE STOP
# ============================================================

def answer_machine_stops(events):

    stops = [
        e for e in events
        if e.get("event_type")
        == "machine_unexpected_stop"
    ]

    if not stops:

        return {
            "status": "no_match",
            "answer": (
                "No machine-specific unexpected stop "
                "was detected."
            ),
            "count": 0,
            "timestamps": []
        }

    unique_stops = []

    for event in sorted(
        stops,
        key=timestamp
    ):

        if not unique_stops:
            unique_stops.append(event)
            continue

        if (
            timestamp(event)
            - timestamp(unique_stops[-1])
            >= 1.0
        ):
            unique_stops.append(event)

    return {
        "status": "answer",
        "answer": (
            f"The machine stopped unexpectedly "
            f"{len(unique_stops)} time(s)."
        ),
        "count": len(unique_stops),
        "timestamps": [
            timestamp(e)
            for e in unique_stops
        ]
    }


# ============================================================
# BEFORE SAFETY ALARM
# ============================================================

def answer_before_alarm(events):

    alarms = [
        e for e in events
        if e.get("event_type")
        == "safety_alarm"
    ]

    if not alarms:

        return {
            "status": "no_match",
            "answer": (
                "No safety alarm was detected."
            ),
            "timestamp": None
        }

    meaningful = meaningful_events(
        events
    )

    results = []

    for alarm in alarms:

        alarm_time = timestamp(alarm)

        previous = [
            e for e in meaningful
            if timestamp(e) < alarm_time
            and e is not alarm
        ]

        previous.sort(
            key=timestamp,
            reverse=True
        )

        prior = (
            previous[0]
            if previous
            else None
        )

        results.append({
            "alarm_timestamp": alarm_time,
            "previous_event": (
                event_label(prior)
                if prior
                else "No earlier event"
            ),
            "previous_timestamp": (
                timestamp(prior)
                if prior
                else None
            )
        })

    first = results[0]

    return {
        "status": "answer",
        "answer": (
            f"{first['previous_event']} at "
            f"{format_time(first['previous_timestamp'])} "
            f"occurred immediately before the safety alarm."
            if first["previous_timestamp"] is not None
            else "No earlier event was available."
        ),
        "timestamp": first["previous_timestamp"],
        "alarm_timestamp": first["alarm_timestamp"],
        "results": results
    }


# ============================================================
# UNTOUCHED OBJECTS
# ============================================================

def answer_untouched(events):

    candidates = []

    for event in events:

        if event.get("event_type") != "object_untouched":
            continue

        duration = event_duration(event)

        if duration is None:
            continue

        if duration >= 120:

            candidates.append({
                "timestamp": timestamp(event),
                "duration_seconds": duration,
                "description": event_label(event)
            })

    if not candidates:

        return {
            "status": "no_match",
            "answer": (
                "No object was verified as untouched "
                "for more than 2 minutes."
            ),
            "objects": [],
            "timestamp": None
        }

    return {
        "status": "answer",
        "answer": (
            f"{len(candidates)} object(s) remained "
            f"untouched for more than 2 minutes."
        ),
        "objects": candidates,
        "timestamp": candidates[0]["timestamp"]
    }


# ============================================================
# BEFORE MOVEMENT STOP
# ============================================================

def answer_before_movement_stop(events):

    stops = [
        e for e in events
        if e.get("event_type")
        == "movement_stopped"
    ]

    if not stops:

        return {
            "status": "no_match",
            "answer": (
                "No movement stop was detected."
            ),
            "timestamp": None
        }

    meaningful = meaningful_events(
        events
    )

    results = []

    for stop in stops:

        stop_time = timestamp(stop)

        previous = [
            e for e in meaningful
            if timestamp(e) < stop_time
            and e is not stop
        ]

        previous.sort(
            key=timestamp,
            reverse=True
        )

        prior = (
            previous[0]
            if previous
            else None
        )

        results.append({
            "stop_timestamp": stop_time,
            "previous_event": (
                event_label(prior)
                if prior
                else "No earlier event"
            ),
            "previous_timestamp": (
                timestamp(prior)
                if prior
                else None
            ),
            "gap_seconds": (
                stop_time - timestamp(prior)
                if prior
                else None
            )
        })

    first = results[0]

    return {
        "status": "answer",
        "answer": (
            f"{first['previous_event']} at "
            f"{format_time(first['previous_timestamp'])} "
            f"occurred immediately before movement stopped "
            f"at {format_time(first['stop_timestamp'])}."
            if first["previous_timestamp"] is not None
            else "No earlier event was available."
        ),
        "timestamp": first["previous_timestamp"],
        "reference_timestamp": first["stop_timestamp"],
        "results": results
    }


# ============================================================
# AFTER MOVEMENT START
# ============================================================

def answer_after_movement_start(events):

    starts = [
        e for e in events
        if e.get("event_type")
        == "movement_started"
    ]

    if not starts:

        return {
            "status": "no_match",
            "answer": (
                "No movement start was detected."
            ),
            "timestamp": None
        }

    meaningful = meaningful_events(
        events
    )

    results = []

    for start in starts:

        start_time = timestamp(start)

        later = [
            e for e in meaningful
            if timestamp(e) > start_time
            and e is not start
        ]

        later.sort(
            key=timestamp
        )

        following = (
            later[0]
            if later
            else None
        )

        results.append({
            "start_timestamp": start_time,
            "next_event": (
                event_label(following)
                if following
                else "No later event"
            ),
            "next_timestamp": (
                timestamp(following)
                if following
                else None
            ),
            "gap_seconds": (
                timestamp(following) - start_time
                if following
                else None
            )
        })

    first = results[0]

    return {
        "status": "answer",
        "answer": (
            f"{first['next_event']} at "
            f"{format_time(first['next_timestamp'])} "
            f"occurred immediately after movement started "
            f"at {format_time(first['start_timestamp'])}."
            if first["next_timestamp"] is not None
            else "No later event was available."
        ),
        "timestamp": first["next_timestamp"],
        "reference_timestamp": first["start_timestamp"],
        "results": results
    }


# ============================================================
# STATIONARY DURATION
# ============================================================

def answer_stationary_duration(events):

    stationary = [
        e for e in events
        if e.get("event_type")
        == "stationary_interval"
    ]

    if not stationary:

        return {
            "status": "no_match",
            "answer": (
                "No stationary interval was detected."
            ),
            "timestamp": None
        }

    valid = []

    for event in stationary:

        duration = event_duration(event)

        if duration is not None:
            valid.append(
                (event, duration)
            )

    if not valid:

        return {
            "status": "no_match",
            "answer": (
                "A stationary interval was detected, "
                "but its duration could not be calculated."
            ),
            "timestamp": timestamp(stationary[0])
        }

    longest, duration = max(
        valid,
        key=lambda x: x[1]
    )

    return {
        "status": "answer",
        "answer": (
            f"The longest stationary interval was "
            f"{duration:.2f} seconds."
        ),
        "duration_seconds": duration,
        "timestamp": timestamp(longest)
    }


# ============================================================
# INTERACTION COUNT
# ============================================================

def answer_interaction_count(events):

    interactions = [
        e for e in events
        if e.get("event_type")
        == "interaction_candidate"
    ]

    return {
        "status": (
            "answer"
            if interactions
            else "no_match"
        ),
        "answer": (
            f"{len(interactions)} interaction "
            f"candidate(s) were detected."
        ),
        "count": len(interactions),
        "timestamps": [
            timestamp(e)
            for e in interactions
        ]
    }


# ============================================================
# QUESTION ROUTER
# ============================================================

def answer_question(question):

    events = load_events()

    intent = classify_question(
        question
    )

    if intent == "restricted_area":

        result = answer_restricted_area(
            events
        )

    elif intent == "machine_stop":

        result = answer_machine_stops(
            events
        )

    elif intent == "before_alarm":

        result = answer_before_alarm(
            events
        )

    elif intent == "untouched":

        result = answer_untouched(
            events
        )

    elif intent == "before_movement_stop":

        result = answer_before_movement_stop(
            events
        )

    elif intent == "after_movement_start":

        result = answer_after_movement_start(
            events
        )

    elif intent == "stationary_duration":

        result = answer_stationary_duration(
            events
        )

    elif intent == "interaction_count":

        result = answer_interaction_count(
            events
        )

    else:

        result = {
            "status": "unsupported",
            "answer": (
                "This question is not yet mapped "
                "to the ChronoVision temporal query engine."
            ),
            "timestamp": None
        }

    result["question"] = question
    result["intent"] = intent

    return result


# ============================================================
# COMMAND LINE
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="ChronoVision PS02 Question Router"
    )

    parser.add_argument(
        "--question",
        required=True
    )

    args = parser.parse_args()

    result = answer_question(
        args.question
    )

    print(
        "\n=== CHRONOVISION ANSWER ==="
    )

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()



