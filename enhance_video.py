import os
import subprocess
import tempfile

import cv2
import numpy as np
from imageio_ffmpeg import get_ffmpeg_exe

from enhancement import process_frame


def _run_ffmpeg(args):
    result = subprocess.run(
        [get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"] + args,
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def _mux_output(video_path: str, raw_path: str, output_path: str, crf: int) -> None:
    try:
        _run_ffmpeg([
            "-i", video_path, "-i", raw_path,
            "-map", "1:v", "-map", "0:a?",
            "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-movflags", "+faststart",
            output_path,
        ])
    except RuntimeError:
        _run_ffmpeg([
            "-i", raw_path,
            "-c:v", "libx264", "-crf", str(crf), "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ])


def _make_compare(original: np.ndarray, enhanced: np.ndarray) -> np.ndarray:
    return np.hstack([original, enhanced])


def enhance_video(video_path: str, output_path: str, strength: float = 1.0,
                  denoise: bool = False, compare: bool = False,
                  crf: int = 18, progress_callback=None,
                  preview_callback=None) -> None:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError("Video konnte nicht gelesen werden.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps <= 0:
        fps = 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width <= 0 or height <= 0:
        cap.release()
        raise ValueError("Video hat keine gueltige Aufloesung.")
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    out_width, out_height = width // 2 * 2, height // 2 * 2
    out_fps = min(fps, 60.0)

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = os.path.join(tmp, "raw.mp4")
        writer = cv2.VideoWriter(raw_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                 out_fps, (out_width, out_height))
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Videoschreiber konnte nicht geoeffnet werden.")

        index = 0
        first_pair = None
        try:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                enhanced = process_frame(frame, strength=strength, denoise=denoise)
                if index == 0 and preview_callback is not None:
                    first_pair = (frame, enhanced)
                if out_width != width or out_height != height:
                    enhanced = cv2.resize(enhanced, (out_width, out_height))
                writer.write(enhanced)
                index += 1
                if progress_callback is not None and total > 0:
                    progress_callback(min(index / total, 1.0))
        finally:
            cap.release()
            writer.release()

        if first_pair is not None:
            preview_callback(first_pair)

        if compare:
            _process_compare(video_path, raw_path, output_path, strength,
                             denoise, out_width, out_height, crf)
        else:
            _mux_output(video_path, raw_path, output_path, crf)


def _process_compare(video_path: str, raw_path: str, output_path: str,
                     strength: float, denoise: bool, out_width: int,
                     out_height: int, crf: int) -> None:
    cap = cv2.VideoCapture(video_path)
    enh = cv2.VideoCapture(raw_path)
    cmp_path = output_path + ".cmp.mp4"
    writer = cv2.VideoWriter(cmp_path, cv2.VideoWriter_fourcc(*"mp4v"),
                             min(cap.get(cv2.CAP_PROP_FPS) or 30.0, 60.0),
                             (out_width * 2, out_height))
    while True:
        ok_a, frame_a = cap.read()
        ok_b, frame_b = enh.read()
        if not ok_a or not ok_b:
            break
        writer.write(_make_compare(frame_a, frame_b))
    cap.release()
    enh.release()
    writer.release()
    _mux_output(video_path, cmp_path, output_path, crf)
    os.remove(cmp_path)
