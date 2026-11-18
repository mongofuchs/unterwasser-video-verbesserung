import cv2
import numpy as np


def _stretch_channel(channel: np.ndarray, low_pct: float, high_pct: float) -> np.ndarray:
    lo, hi = np.percentile(channel, (low_pct, high_pct))
    if hi - lo < 1e-6:
        return channel
    stretched = (channel.astype(np.float32) - lo) * 255.0 / (hi - lo)
    return np.clip(stretched, 0, 255)


def histogram_stretch(image: np.ndarray, strength: float) -> np.ndarray:
    low_pct, high_pct = 1.5 * strength, 100.0 - 1.5 * strength
    channels = [_stretch_channel(image[..., c], low_pct, high_pct) for c in range(3)]
    return np.stack(channels, axis=-1).astype(np.uint8)


def white_balance(image: np.ndarray, strength: float) -> np.ndarray:
    result = image.astype(np.float32)
    means = result.reshape(-1, 3).mean(axis=0)
    gray = means.mean()
    max_gain = 1.15 + 0.2 * strength
    gains = np.clip(gray / np.maximum(means, 1e-6), 1.0 / max_gain, max_gain)
    return np.clip(result * gains, 0, 255).astype(np.uint8)


def apply_clahe(image: np.ndarray, clip_limit: float) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    lab[..., 0] = clahe.apply(lab[..., 0])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def boost_saturation(image: np.ndarray, factor: float) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[..., 1] = np.clip(hsv[..., 1] * factor, 0, 255)
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)


def denoise_frame(image: np.ndarray, strength: int) -> np.ndarray:
    if strength <= 0:
        return image
    return cv2.fastNlMeansDenoisingColored(image, None, strength, strength, 7, 21)


def process_frame(image: np.ndarray, strength: float = 1.0,
                  denoise: bool = False) -> np.ndarray:
    if denoise:
        image = denoise_frame(image, 5)
    image = histogram_stretch(image, strength)
    image = white_balance(image, strength)
    image = apply_clahe(image, 1.5 * strength)
    image = boost_saturation(image, 1.0 + 0.15 * strength)
    return image
