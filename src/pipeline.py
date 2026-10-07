import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def run_step(label, command):
    print()
    print("=" * 64)
    print(label)
    print("=" * 64)

    result = subprocess.run(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    print(result.stdout)

    if result.returncode != 0:
        raise RuntimeError(
            f"{label} failed with exit code "
            f"{result.returncode}"
        )


def main():
    parser = argparse.ArgumentParser(
        description="ChronoVision end-to-end video pipeline"
    )

    parser.add_argument(
        "--video",
        required=True,
    )

    parser.add_argument(
        "--tracker",
        default="botsort.yaml",
    )

    parser.add_argument(
        "--zone",
        default=None,
    )

    parser.add_argument(
        "--device",
        default="0",
    )

    args = parser.parse_args()

    video = Path(args.video)

    if not video.exists():
        raise FileNotFoundError(
            f"Video not found: {video}"
        )

    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + " CHRONOVISION ANALYSIS PIPELINE".ljust(62) + "║")
    print("╚" + "═" * 62 + "╝")
    print()
    print(f"Video:   {video}")
    print(f"Tracker: {args.tracker}")
    print(f"Device:  {args.device}")

    # --------------------------------------------------------
    # 1. TRACKING
    # --------------------------------------------------------

    run_step(
        "STEP 1 — DETECTION + TRACKING",
        [
            sys.executable,
            "src/tracking.py",
            "--video",
            str(video),
            "--out-dir",
            "runtime/tracks",
            "--device",
            args.device,
            "--tracker",
            args.tracker,
        ],
    )

    # --------------------------------------------------------
    # 2. MOVEMENT EVENTS
    # --------------------------------------------------------

    run_step(
        "STEP 2 — MOVEMENT EVENT EXTRACTION",
        [
            sys.executable,
            "src/events.py",
            "--tracks",
            "runtime/tracks/tracks.jsonl",
            "--summary",
            "runtime/tracks/track_summary.json",
            "--out-dir",
            "runtime/events",
        ],
    )

    # --------------------------------------------------------
    # 3. ZONE EVENTS
    # --------------------------------------------------------

    if args.zone:
        run_step(
            "STEP 3 — SPATIAL ZONE ANALYSIS",
            [
                sys.executable,
                "src/zones.py",
                "--tracks",
                "runtime/tracks/tracks.jsonl",
                "--summary",
                "runtime/tracks/track_summary.json",
                "--zone",
                args.zone,
                "--out-dir",
                "runtime/events",
            ],
        )
    else:
        print()
        print("=" * 64)
        print("STEP 3 — SPATIAL ZONE ANALYSIS")
        print("=" * 64)
        print("Skipped: no zone configuration supplied.")

    # --------------------------------------------------------
    # 4. INTERACTIONS
    # --------------------------------------------------------

    run_step(
        "STEP 4 — INTERACTION CANDIDATE ANALYSIS",
        [
            sys.executable,
            "src/interactions.py",
            "--tracks",
            "runtime/tracks/tracks.jsonl",
            "--summary",
            "runtime/tracks/track_summary.json",
            "--out-dir",
            "runtime/events",
        ],
    )

    # --------------------------------------------------------
    # 5. MERGE
    # --------------------------------------------------------

    run_step(
        "STEP 5 — UNIFIED EVENT GRAPH",
        [
            sys.executable,
            "src/merge_events.py",
            "--base",
            "runtime/events/events.jsonl",
            "--zone",
            "runtime/events/zone_events.jsonl",
            "--interaction",
            "runtime/events/interaction_events.jsonl",
            "--output",
            "runtime/events/all_events.jsonl",
        ],
    )

    # --------------------------------------------------------
    # COMPLETE
    # --------------------------------------------------------

    print()
    print("╔" + "═" * 62 + "╗")
    print("║" + " CHRONOVISION ANALYSIS COMPLETE".ljust(62) + "║")
    print("╚" + "═" * 62 + "╝")

    print()
    print("Generated:")
    print("  runtime/tracks/tracks.jsonl")
    print("  runtime/tracks/track_summary.json")
    print("  runtime/events/events.jsonl")
    print("  runtime/events/interaction_events.jsonl")
    print("  runtime/events/all_events.jsonl")

    if args.zone:
        print(
            "  runtime/events/zone_events.jsonl"
        )

    print()
    print("PIPELINE COMPLETE")


if __name__ == "__main__":
    main()