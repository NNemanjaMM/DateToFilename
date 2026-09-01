"""Rank images by likely quality and cluster near-identical ones."""

from .config import Config
from .model import ImageInfo
from .refine import refine_groups

Group = list[ImageInfo]


def quality_score(info: ImageInfo) -> float:
    """
    Higher score = probably the better copy.

    Resolution dominates; file size breaks ties; HEIC/HEIF gets a small nudge
    because camera originals are often stored in that format.
    """
    score = float(info.pixels)
    score += info.file_size / 100

    if info.image_format.upper() in ("HEIC", "HEIF"):
        score += 100_000

    return score


def sort_by_quality(group: Group) -> None:
    """Sort in place, best copy first."""
    group.sort(key=quality_score, reverse=True)


def find_duplicate_groups(images: list[ImageInfo], config: Config) -> list[Group]:
    """
    Greedy clustering: each image joins the first existing group whose anchor
    is within hash_distance, otherwise it starts a new group. Only groups with
    more than one member are returned.

    When ``config.pixel_check`` is set, the perceptual-hash groups are only
    candidates: each one is then confirmed pixel-by-pixel (see
    :mod:`dupfinder.refine`) and split where the images are not really alike.
    """
    groups: list[Group] = []

    for image in images:
        for group in groups:
            if image.distance_to(group[0]) <= config.hash_distance:
                group.append(image)
                break
        else:
            groups.append([image])

    candidates = [group for group in groups if len(group) > 1]

    if config.pixel_check and candidates:
        print(
            f"\n  Hash pass found {len(candidates)} candidate group(s). "
            f"Confirming pixel-by-pixel at {config.pixel_size}px "
            f"(SSIM >= {config.pixel_similarity:.2f})..."
        )
        candidates = refine_groups(candidates, config)

    return candidates
