import os
import json
import time
import argparse
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from pydantic import BaseModel, Field


MODEL = "gemini-3.5-flash-lite"

OUTPUT_DIR = Path("runtime/events")
OUTPUT_FILE = OUTPUT_DIR / "semantic_events.jsonl"


class SemanticEvent(BaseModel):
    event_type: str = Field(
        description=(
            "One of: truck_arrived, machine_unexpected_stop, "
            "safety_alarm, object_untouched, person_action, object_action"
        )
    )

    timestamp: float = Field(ge=0)

    end_timestamp: Optional[float] = Field(
        default=None,
        ge=0
    )

    description: str

    subject: Optional[str] = None

    subject_id: Optional[str] = None

    confidence: float = Field(
        ge=0,
        le=1
    )

    evidence: Optional[str] = None


class SemanticEventSet(BaseModel):
    events: list[SemanticEvent] = Field(
        default_factory=list
    )


def get_client():

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured in this CMD session."
        )

    return genai.Client(
        api_key=api_key
    )


def upload_video(client, video_path):

    print("Uploading video to Gemini...")

    video_file = client.files.upload(
        file=str(video_path)
    )

    while True:

        state = getattr(
            getattr(
                video_file,
                "state",
                None
            ),
            "name",
            None
        )

        print(
            f"Video state: {state}"
        )

        if state == "ACTIVE":

            print(
                "Video ready."
            )

            return video_file

        if state in {"FAILED", "ERROR"}:

            raise RuntimeError(
                f"Video processing failed: {state}"
            )

        time.sleep(3)

        video_file = client.files.get(
            name=video_file.name
        )


def save_events(event_set):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        for event in event_set.events:

            record = event.model_dump()

            record["source"] = "gemini_semantic"

            record["timestamp_source"] = (
                "gemini_approximate"
            )

            record["verified"] = False

            f.write(
                json.dumps(
                    record,
                    ensure_ascii=False
                ) + "\n"
            )


def analyze_video(video_path):

    client = get_client()

    print(
        "=== ChronoVision Semantic Event Engine ==="
    )

    print(
        f"Video: {video_path}"
    )

    print(
        f"Model: {MODEL}"
    )

    video_file = upload_video(
        client,
        video_path
    )

    prompt = """
You are the semantic event analysis component of ChronoVision,
a video understanding and temporal reasoning system.

Analyze the entire video.

Identify only events that are directly supported by visual or audio evidence.

Look for:

1. Truck arrival
2. Unexpected machine stop
3. Safety alarm
4. Object remaining untouched for a long period
5. Person actions
6. Object actions

For every detected event return:

- event type
- approximate timestamp in seconds
- optional end timestamp
- concise description
- subject
- confidence from 0 to 1
- evidence

Important rules:

- Do NOT invent events.
- Do NOT invent timestamps.
- Do NOT claim causation just because one event happened before another.
- Temporal order is not automatically causation.
- Prefer reliable events over speculative events.
- These timestamps are semantic candidate timestamps.
- ChronoVision's local CV pipeline remains authoritative for
  tracking and final timestamp verification.
"""

    print(
        "Sending video to Gemini for semantic analysis..."
    )

    response = client.models.generate_content(
        model=MODEL,
        contents=[
            video_file,
            prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=SemanticEventSet,
            temperature=0.1,
        ),
    )

    print(
        "Gemini analysis complete."
    )

    # Prefer SDK-parsed Pydantic result
    parsed = getattr(
        response,
        "parsed",
        None
    )

    if parsed is not None:

        if isinstance(parsed, SemanticEventSet):

            event_set = parsed

        else:

            event_set = SemanticEventSet.model_validate(
                parsed
            )

    else:

        text = (
            getattr(
                response,
                "text",
                ""
            ) or ""
        ).strip()

        if not text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        event_set = SemanticEventSet.model_validate(
            json.loads(text)
        )

    save_events(
        event_set
    )

    print(
        "\n=== Semantic Events ==="
    )

    print(
        f"Events detected: {len(event_set.events)}"
    )

    for event in event_set.events:

        if event.end_timestamp is not None:

            timestamp = (
                f"{event.timestamp:.3f}s"
                f" -> "
                f"{event.end_timestamp:.3f}s"
            )

        else:

            timestamp = (
                f"{event.timestamp:.3f}s"
            )

        print(
            f"- {timestamp} | "
            f"{event.event_type} | "
            f"{event.description} | "
            f"confidence={event.confidence:.2f}"
        )

    print(
        f"\nSaved to: {OUTPUT_FILE}"
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "ChronoVision Gemini semantic event engine"
        )
    )

    parser.add_argument(
        "--video",
        required=True
    )

    args = parser.parse_args()

    try:

        analyze_video(
            args.video
        )

    except KeyboardInterrupt:

        print(
            "\nStopped by user."
        )

    except Exception as exc:

        print(
            "\n=== ERROR ==="
        )

        print(
            f"{type(exc).__name__}: {exc}"
        )

        raise


if __name__ == "__main__":

    main()
