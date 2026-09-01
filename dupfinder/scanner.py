"""Find candidate image files and read the facts we need about each one."""

import os
from pathlib import Path

import imagehash
from PIL import Image
from pillow_heif import register_heif_opener

from .config import Config
from .model import ImageInfo

# Let Pillow open HEIC/HEIF (iPhone originals)
register_heif_opener()


def scan_files(config: Config) -> list[Path]:
    files: list[Path] = []

    for root, dirs, filenames in os.walk(config.source_dir):
        # Never descend into the folder we move duplicates into
        dirs[:] = [d for d in dirs if Path(root, d) != config.duplicates_dir]

        for filename in filenames:
            path = Path(root) / filename
            if path.suffix.lower() in config.supported_extensions:
                files.append(path)

    return files


def read_image_info(path: Path) -> ImageInfo | None:
    try:
        with Image.open(path) as image:
            width, height = image.size
            return ImageInfo(
                path=path,
                phash=imagehash.phash(image),
                width=width,
                height=height,
                file_size=path.stat().st_size,
                image_format=image.format or "",
            )
    except Exception as e:
        print(f"\nERROR reading:\n  {path}\n  {e}")
        return None


def analyze(files: list[Path], progress_every: int = 100) -> list[ImageInfo]:
    images: list[ImageInfo] = []

    for index, path in enumerate(files, 1):
        info = read_image_info(path)
        if info is not None:
            images.append(info)

        if progress_every and index % progress_every == 0:
            print(f"  Processed {index}/{len(files)}")

    return images
