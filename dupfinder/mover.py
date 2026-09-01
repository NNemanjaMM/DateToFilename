"""Work out where a duplicate should go and move it there."""

import shutil
from pathlib import Path

from .config import Config
from .grouping import Group, sort_by_quality


def destination_for(path: Path, config: Config) -> Path:
    """Mirror the file's location under _duplicates/, never overwriting."""
    destination = config.duplicates_dir / path.relative_to(config.source_dir)

    if destination.exists():
        stem, suffix = destination.stem, destination.suffix
        counter = 1
        while destination.exists():
            destination = destination.parent / f"{stem}_duplicate_{counter}{suffix}"
            counter += 1

    return destination


def move_files(paths: list[Path], config: Config) -> tuple[int, int]:
    """Move each path into _duplicates/. Returns (moved, errors)."""
    moved = 0
    errors = 0

    for source in paths:
        if not source.exists():
            print(f"  SKIP (missing): {source}")
            continue

        try:
            destination = destination_for(source, config)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))
            print(f"  MOVE: {source}")
            print(f"     -> {destination}")
            moved += 1
        except Exception as e:
            print(f"\nERROR moving:\n  {source}\n  {e}")
            errors += 1

    return moved, errors


def non_keeper_paths(groups: list[Group]) -> list[Path]:
    """Every file except the best copy of each group (the move-all fallback)."""
    paths: list[Path] = []

    for group in groups:
        sort_by_quality(group)
        paths.extend(info.path for info in group[1:])

    return paths
