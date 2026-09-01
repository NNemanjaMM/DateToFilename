"""All tunable settings live here, plus the derived output paths."""

from dataclasses import dataclass
from pathlib import Path

DEFAULT_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"})


@dataclass
class Config:
    source_dir: Path

    # Perceptual hash tolerance.
    #   0     = identical
    #   1-3   = very similar
    #   4-5   = more tolerant
    hash_distance: int = 0

    # Second-stage check. The perceptual hash only sees the coarse light/dark
    # layout of a frame, so burst shots (a turned head, an object that appears)
    # can hash the same. When this is on, every candidate group is re-examined
    # pixel-by-pixel at low resolution and split apart where the images are not
    # actually structurally similar.
    pixel_check: bool = True
    pixel_size: int = 128            # images are compared as pixel_size x pixel_size
    pixel_similarity: float = 0.90   # SSIM >= this counts as the same photo
                                     #   ~1.00  identical / re-encoded / resized
                                     #   0.93+  safe "same photo"
                                     #   <0.90  different moment (raise to be stricter)

    # True  = one self-contained HTML file (thumbnails baked in as base64).
    # False = smaller HTML + a _duplicate_report_assets folder that must stay beside it.
    embed_thumbnails: bool = True
    thumbnail_max_px: int = 480

    supported_extensions: frozenset[str] = DEFAULT_EXTENSIONS

    # ---- Derived paths (all inside source_dir) ----

    @property
    def duplicates_dir(self) -> Path:
        return self.source_dir / "_duplicates"

    @property
    def report_file(self) -> Path:
        return self.source_dir / "_duplicate_report.html"

    @property
    def decisions_file(self) -> Path:
        return self.source_dir / "_duplicate_decisions.json"

    @property
    def assets_dir(self) -> Path:
        return self.source_dir / "_duplicate_report_assets"
