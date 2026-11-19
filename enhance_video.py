import os
import subprocess
import tempfile
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

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


def _process_worker(frame: np.ndarray, strength: float, denoise: bool) -> np.ndarray:
    return process_frame(frame, strength=strength, denoise=denoise)


def _format_eta(seconds: float) -> str:
    if not seconds or seconds == float("inf") or seconds < 0:
        return ""
    seconds = int(seconds)
    if seconds >= 3600:
        return f"{seconds // 3600} h {(seconds % 3600) // 60} min"
    if seconds >= 60:
        return f"{seconds // 60} min"
    return f"{seconds} s"


def enhance_video(video_path: str, output_path: str, strength: float = 1.0,
                  denoise: bool = False, compare: bool = False,
                  crf: int = 18, progress_callback=None,
                  preview_callback=None, workers: int = None) -> None:
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

    if workers is None:
        workers = max(1, min(8, (os.cpu_count() or 1) - 1))
    batch = max(2, workers * 2)

    out_width, out_height = width // 2 * 2, height // 2 * 2
    out_fps = min(fps, 60.0)

    start_time = time.monotonic()

    with tempfile.TemporaryDirectory() as tmp:
        raw_path = os.path.join(tmp, "raw.mp4")
        writer = cv2.VideoWriter(raw_path, cv2.VideoWriter_fourcc(*"mp4v"),
                                 out_fps, (out_width, out_height))
        if not writer.isOpened():
            cap.release()
            raise RuntimeError("Videoschreiber konnte nicht geoeffnet werden.")

        index = 0
        next_to_write = 0
        read_failed = False
        pending = OrderedDict()
        first_pair = None
        first_pair_done = False

        try:
            with ThreadPoolExecutor(max_workers=workers) as ex:
                while True:
                    if not read_failed:
                        ok, frame = cap.read()
                        if ok:
                            pending[index] = (frame, ex.submit(
                                _process_worker, frame, strength, denoise))
                            index += 1
                        else:
                            read_failed = True
                    if len(pending) >= batch or (read_failed and pending):
                        original, future = pending.pop(next_to_write)
                        enhanced = future.result()
                        if not first_pair_done and preview_callback is not None:
                            first_pair_done = True
                            first_pair = (original, enhanced)
                        if out_width != enhanced.shape[1] or out_height != enhanced.shape[0]:
                            enhanced = cv2.resize(enhanced, (out_width, out_height))
                        writer.write(enhanced)
                        next_to_write += 1
                        if progress_callback is not None and total > 0:
                            frac = min(next_to_write / total, 1.0)
                            elapsed = time.monotonic() - start_time
                            eta = _format_eta(
                                elapsed / max(next_to_write, 1)
                                * (total - next_to_write))
                            desc = "Verarbeite Frames"
                            if eta:
                                desc += f" (ca. {eta} verbleibend)"
                            progress_callback(frac, desc=desc)
                    if read_failed and not pending:
                        break
        finally:
            cap.release()
            writer.release()

        if first_pair is not None and preview_callback is not None:
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
