import argparse
import json
import re
from pathlib import Path

from reasoning import (
    BOOKKEEPING_EVENTS,
    detect_event_type,
    format_event,
    load_events,
)


def split_temporal_query(query):
    q = query.lower().strip()

    match = re.search(
        r"\b(immediately\s+before|immediately\s+after|before|after)\b",
        q,
    )

    if not match:
        return None

    relation_text = match.group(1)
    relation = relation_text.replace(" ", "_").upper()

    left = q[:match.start()].strip()
    right = q[match.end():].strip()

    return left, relation, right


def clean_clause(clause):
    clause = clause.strip(" ?.,!")

    clause = re.sub(
        r"^(what|which|who|where|when|did|does|is|was|were)\b",
        "",
        clause,
    ).strip()

    clause = re.sub(
        r"^(the|a|an)\b",
        "",
        clause,
    ).strip()

    return clause


def meaningful_events(events):
    return [
        event
        for event in events
        if event.get("event_type")
        not in BOOKKEEPING_EVENTS
    ]


def find_closest_after(events, reference, immediate=False):
    candidates = [
        event
        for event in meaningful_events(events)
        if event["time_sec"] > reference["time_sec"]
    ]

    if not candidates:
        return []

    candidates.sort(
        key=lambda e: e["time_sec"] - reference["time_sec"]
    )

    return candidates[:1] if immediate else candidates


def find_closest_before(events, reference, immediate=False):
    candidates = [
        event
        for event in meaningful_events(events)
        if event["time_sec"] < reference["time_sec"]
    ]

    if not candidates:
        return []

    candidates.sort(
        key=lambda e: reference["time_sec"] - e["time_sec"]
    )

    return candidates[:1] if immediate else candidates


def answer_open_query(query, relation, reference_type, events):
    references = [
        event
        for event in meaningful_events(events)
        if event.get("event_type") == reference_type
    ]

    if not references:
        return {
            "query": query,
            "status": "no_match",
            "answer": (
                f"No '{reference_type}' event was found."
            ),
        }

    results = []

    for reference in references:
        if relation == "IMMEDIATELY_AFTER":
            related = find_closest_after(
                events,
                reference,
                immediate=True,
            )
        elif relation == "AFTER":
            related = find_closest_after(
                events,
                reference,
                immediate=False,
            )
        elif relation == "IMMEDIATELY_BEFORE":
            related = find_closest_before(
                events,
                reference,
                immediate=True,
            )
        else:
            related = find_closest_before(
                events,
                reference,
                immediate=False,
            )

        if related:
            results.append(
                {
                    "reference_event": format_event(
                        reference
                    ),
                    "related_events": [
                        format_event(event)
                        for event in related
                    ],
                }
            )

    if not results:
        return {
            "query": query,
            "status": "no_match",
            "answer": (
                f"No event found {relation.lower().replace('_', ' ')} "
                f"the reference event."
            ),
        }

    return {
        "query": query,
        "status": "success",
        "answer_type": "OPEN_TEMPORAL",
        "relation": relation,
        "reference_event_type": reference_type,
        "answers": results,
    }


def answer_comparative_query(query, events):
    parsed = split_temporal_query(query)

    if not parsed:
        return {
            "query": query,
            "status": "unsupported",
            "answer": "No temporal relation detected.",
        }

    left_clause, relation, right_clause = parsed

    left_clause = clean_clause(left_clause)
    right_clause = clean_clause(right_clause)

    target_type = detect_event_type(left_clause)
    reference_type = detect_event_type(right_clause)

    # Open-ended form:
    # "What happened immediately after movement started?"
    if (
        left_clause in {
            "",
            "happened",
            "happened immediately",
            "what happened",
        }
        and reference_type
    ):
        return answer_open_query(
            query,
            relation,
            reference_type,
            events,
        )

    # Comparative form:
    # "Which person entered zone after movement started?"
    if not target_type or not reference_type:
        return {
            "query": query,
            "status": "unsupported",
            "answer": (
                "Could not identify both the target "
                "and reference event types."
            ),
            "target_clause": left_clause,
            "reference_clause": right_clause,
        }

    targets = [
        event
        for event in meaningful_events(events)
        if event.get("event_type") == target_type
    ]

    references = [
        event
        for event in meaningful_events(events)
        if event.get("event_type") == reference_type
    ]

    matches = []

    for target in targets:
        valid_references = []

        for reference in references:
            if relation in {
                "AFTER",
                "IMMEDIATELY_AFTER",
            }:
                valid = (
                    target["time_sec"]
                    > reference["time_sec"]
                )
            else:
                valid = (
                    target["time_sec"]
                    < reference["time_sec"]
                )

            if valid:
                valid_references.append(reference)

        if not valid_references:
            continue

        if relation in {
            "AFTER",
            "IMMEDIATELY_AFTER",
        }:
            closest = min(
                valid_references,
                key=lambda event:
                    target["time_sec"]
                    - event["time_sec"],
            )
        else:
            closest = min(
                valid_references,
                key=lambda event:
                    event["time_sec"]
                    - target["time_sec"],
            )

        matches.append(
            {
                "target_event": format_event(target),
                "reference_event": format_event(closest),
                "time_gap_sec": round(
                    abs(
                        target["time_sec"]
                        - closest["time_sec"]
                    ),
                    3,
                ),
            }
        )

    if not matches:
        return {
            "query": query,
            "status": "no_match",
            "answer": (
                "No target event satisfies "
                f"the {relation.lower()} relation."
            ),
            "target_event_type": target_type,
            "reference_event_type": reference_type,
        }

    if relation in {
        "IMMEDIATELY_AFTER",
        "IMMEDIATELY_BEFORE",
    }:
        matches = matches[:1]

    return {
        "query": query,
        "status": "success",
        "answer_type": "COMPARATIVE_TEMPORAL",
        "relation": relation,
        "target_event_type": target_type,
        "reference_event_type": reference_type,
        "matches": matches,
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--events",
        default="runtime/events/all_events.jsonl",
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

    result = answer_comparative_query(
        args.query,
        events,
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    if result.get("status") == "success":
        print(
            "STEP 11 ADVANCED TEMPORAL "
            "QUERY COMPLETE"
        )
    else:
        print(
            "STEP 11 QUERY:",
            result.get("status"),
        )


if __name__ == "__main__":
    main()

