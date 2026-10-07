import argparse
import subprocess
from pathlib import Path


def run_command(command):
    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "FFmpeg command failed:\n\n"
            + result.stderr
        )


def extract_frame(video, timestamp, output):
    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(max(0.0, timestamp)),
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-q:v",
        "2",
        str(output),
    ]

    run_command(command)


def extract_clip(video, start, end, output):
    output.parent.mkdir(parents=True, exist_ok=True)

    duration = max(0.5, end - start)

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(max(0.0, start)),
        "-i",
        str(video),
        "-t",
        str(duration),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(output),
    ]

    run_command(command)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--video",
        default="demo_input.mp4",
    )

    parser.add_argument(
        "--time",
        required=True,
        type=float,
    )

    parser.add_argument(
        "--before",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--after",
        type=float,
        default=2.0,
    )

    parser.add_argument(
        "--out-dir",
        default="runtime/evidence",
    )

    args = parser.parse_args()

    video = Path(args.video)
    out_dir = Path(args.out_dir)

    if not video.exists():
        raise FileNotFoundError(
            f"Video not found: {video}"
        )

    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = max(0.0, args.time)
    start = max(0.0, timestamp - args.before)
    end = timestamp + args.after

    frame_path = (
        out_dir
        / f"frame_{timestamp:.3f}s.jpg"
    )

    clip_path = (
        out_dir
        / f"evidence_{start:.3f}s_{end:.3f}s.mp4"
    )

    print("=== ChronoVision Evidence Engine ===")
    print(f"Video: {video}")
    print(f"Event timestamp: {timestamp:.3f}s")
    print(f"Evidence window: {start:.3f}s → {end:.3f}s")

    extract_frame(
        video,
        timestamp,
        frame_path,
    )

    extract_clip(
        video,
        start,
        end,
        clip_path,
    )

    print()
    print(f"Frame: {frame_path}")
    print(f"Clip: {clip_path}")
    print("STEP 5 COMPLETE")


if __name__ == "__main__":
    main()