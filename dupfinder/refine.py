"""Second-stage duplicate check.

The perceptual hash in :mod:`dupfinder.scanner` reduces a whole photo to an
8x8 grid of low-frequency brightness, so it only "sees" the broad composition.
Two frames from a burst - someone turning their head, an object appearing in
one shot - keep the same broad composition and therefore hash the same.

This module takes the candidate groups the hash produced and confirms them the
expensive way: it re-reads each image, shrinks it to ``pixel_size`` square
greyscale, and compares every image to its group's representative with SSIM
(structural similarity). Images that are not genuinely similar are split off,
and any group that falls back to a single member is dropped.
"""

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps
from scipy.ndimage import uniform_filter

from .config import Config
from .model import ImageInfo

Group = list[ImageInfo]


def _load_pixels(path: Path, size: int) -> np.ndarray:
    """EXIF-rotated greyscale image as a float array in [0, 1], size x size."""
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("L").resize((size, size), Image.BILINEAR)
        return np.asarray(image, dtype=np.float64) / 255.0


def _ssim(a: np.ndarray, b: np.ndarray, window: int = 7) -> float:
    """Mean structural similarity between two equally sized greyscale arrays.

    Standard Wang et al. SSIM with a uniform (box) window. Returns ~1.0 for
    identical images and drops as local structure diverges.
    """
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2

    mu_a = uniform_filter(a, window)
    mu_b = uniform_filter(b, window)

    mu_a2 = mu_a * mu_a
    mu_b2 = mu_b * mu_b
    mu_ab = mu_a * mu_b

    var_a = uniform_filter(a * a, window) - mu_a2
    var_b = uniform_filter(b * b, window) - mu_b2
    cov_ab = uniform_filter(a * b, window) - mu_ab

    numerator = (2 * mu_ab + c1) * (2 * cov_ab + c2)
    denominator = (mu_a2 + mu_b2 + c1) * (var_a + var_b + c2)
    return float((numerator / denominator).mean())


def _split_group(group: Group, config: Config) -> list[Group]:
    """Re-cluster one candidate group using pixel-level similarity.

    Each image joins the first sub-group whose representative it matches
    (SSIM >= ``pixel_similarity``); otherwise it starts a new sub-group.
    An image that cannot be re-read is left on its own (i.e. not treated as a
    confirmed duplicate).
    """
    pixels: dict[Path, np.ndarray | None] = {}
    for info in group:
        try:
            pixels[info.path] = _load_pixels(info.path, config.pixel_size)
        except Exception as e:
            print(f"\nERROR re-reading for pixel check:\n  {info.path}\n  {e}")
            pixels[info.path] = None

    subgroups: list[Group] = []
    for info in group:
        arr = pixels[info.path]
        if arr is not None:
            for subgroup in subgroups:
                anchor = pixels[subgroup[0].path]
                if anchor is not None and _ssim(anchor, arr) >= config.pixel_similarity:
                    subgroup.append(info)
                    break
            else:
                subgroups.append([info])
        else:
            subgroups.append([info])

    return subgroups


def refine_groups(groups: list[Group], config: Config) -> list[Group]:
    """Confirm every candidate group pixel-by-pixel; keep only real matches."""
    confirmed: list[Group] = []
    images_in = sum(len(group) for group in groups)
    groups_touched = 0

    for number, group in enumerate(groups, 1):
        subgroups = _split_group(group, config)
        kept = [sub for sub in subgroups if len(sub) > 1]

        if len(subgroups) > 1:
            groups_touched += 1
            largest = max((len(sub) for sub in subgroups), default=0)
            print(
                f"  Group {number}: {len(group)} candidate(s) -> "
                + (
                    "not duplicates, dropped."
                    if not kept
                    else f"confirmed {sum(len(sub) for sub in kept)} in "
                    f"{len(kept)} real group(s) (largest {largest})."
                )
            )

        confirmed.extend(kept)

    images_out = sum(len(group) for group in confirmed)
    print(
        f"  Pixel check: {len(groups)} candidate group(s) / {images_in} image(s) "
        f"-> {len(confirmed)} confirmed group(s) / {images_out} image(s); "
        f"{groups_touched} group(s) changed, {images_in - images_out} image(s) ruled out."
    )

    return confirmed
