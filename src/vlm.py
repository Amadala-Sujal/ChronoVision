import argparse
import json
import os
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class VerificationResult(BaseModel):
    verdict: Literal[
        "verified",
        "rejected",
        "uncertain",
    ] = Field(
        description="Whether the claimed event is visually supported."
    )

    action: str = Field(
        description="Concise description of what is visually happening."
    )

    participants: list[str] = Field(
        description="Visible participants relevant to the event."
    )

    evidence_timestamp_hint: float | None = Field(
        default=None,
        description=(
            "Approximate timestamp within the supplied clip where "
            "the key action is most visible."
        ),
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Semantic confidence from 0 to 1.",
    )

    explanation: str = Field(
        description="Brief explanation grounded only in visible evidence."
    )


def get_client():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None

    from google import genai

    return genai.Client(
        api_key=api_key
    )


def verify_clip(
    video_path: Path,
    claim: str,
    event_timestamp: float,
):
    client = get_client()

    if client is None:
        return {
            "status": "disabled",
            "reason": (
                "GEMINI_API_KEY is not configured. "
                "Local CV evidence remains authoritative."
            ),
            "claim": claim,
            "event_timestamp": event_timestamp,
        }

    from google import genai

    print("Uploading evidence clip to Gemini...")

    video_file = client.files.upload(
        file=str(video_path)
    )

    while (
        not video_file.state
        or video_file.state.name != "ACTIVE"
    ):
        print(
            "Video processing:",
            video_file.state,
        )

        time.sleep(2)

        video_file = client.files.get(
            name=video_file.name
        )

    prompt = f"""
You are the semantic verification layer of ChronoVision.

The deterministic computer-vision system has already identified
an event at timestamp {event_timestamp:.3f} seconds in the original
video.

Claim to verify:
{claim}

Inspect ONLY the supplied evidence clip.

Do not invent events.
Do not provide a more precise timestamp than the visual evidence supports.
Do not override the supplied event timestamp.

Determine whether the claim is visually supported.
"""

    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=[
            video_file,
            prompt,
        ],
        config={
            "response_mime_type": "application/json",
            "response_schema": VerificationResult,
        },
    )

    result = VerificationResult.model_validate_json(
        response.text
    )

    return {
        "status": "verified_by_vlm",
        "claim": claim,
        "event_timestamp": event_timestamp,
        "result": result.model_dump(),
    }


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--video",
        required=True,
    )

    parser.add_argument(
        "--claim",
        required=True,
    )

    parser.add_argument(
        "--timestamp",
        required=True,
        type=float,
    )

    parser.add_argument(
        "--output",
        default="runtime/vlm_verification.json",
    )

    args = parser.parse_args()

    video = Path(args.video)

    if not video.exists():
        raise FileNotFoundError(
            f"Video not found: {video}"
        )

    result = verify_clip(
        video_path=video,
        claim=args.claim,
        event_timestamp=args.timestamp,
    )

    output = Path(args.output)

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.write_text(
        json.dumps(
            result,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(
        json.dumps(
            result,
            indent=2,
        )
    )

    print(
        f"Saved: {output}"
    )

    if result["status"] == "disabled":
        print(
            "STEP 12 VLM MODULE READY "
            "(API KEY NOT CONFIGURED)"
        )
    else:
        print(
            "STEP 12 VLM VERIFICATION COMPLETE"
        )


if __name__ == "__main__":
    main()