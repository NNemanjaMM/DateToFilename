"""The one data record passed between stages."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from imagehash import ImageHash


@dataclass
class ImageInfo:
    path: Path
    phash: "ImageHash"
    width: int
    height: int
    file_size: int
    image_format: str

    @property
    def pixels(self) -> int:
        return self.width * self.height

    def distance_to(self, other: "ImageInfo") -> int:
        """Hamming distance between the two perceptual hashes."""
        return self.phash - other.phash
