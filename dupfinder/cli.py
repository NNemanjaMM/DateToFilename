"""Terminal front end: run the pipeline, print progress, apply decisions."""

from pathlib import Path

from .config import Config
from .decisions import find_decisions_file, load_decisions, resolve_moves
from .grouping import find_duplicate_groups
from .mover import move_files, non_keeper_paths
from .report import write_report
from .scanner import analyze, scan_files

_YES = ("y", "yes")


def _banner(text: str) -> None:
    print("=" * 70)
    print(text)
    print("=" * 70)


def _do_move(paths, config: Config) -> None:
    print()
    _banner("MOVING DUPLICATES")
    print()
    moved, errors = move_files(paths, config)
    print()
    _banner("MOVING COMPLETE")
    print()
    print(f"Files moved: {moved}")
    print(f"Errors:      {errors}")


def _move_from_decisions(decisions_path: Path, config: Config) -> None:
    """Fast path: move exactly what an existing decisions file marks 'move'."""
    decisions = load_decisions(decisions_path, config)
    if not decisions:
        print(f"No usable decisions in:\n  {decisions_path}\nNo files were moved.")
        return

    to_move = [Path(path) for path, choice in decisions.items() if choice == "move"]

    print(f"Decisions file:  {decisions_path}")
    print(f"Files to move:   {len(to_move)}\n")

    if not to_move:
        print("Nothing is marked for moving. No files were moved.")
        return

    _do_move(to_move, config)


def _apply_decisions(groups, config: Config) -> None:
    decisions_path = find_decisions_file(config)

    if decisions_path is None:
        print("No _duplicate_decisions.json found.")
        print('Open the review page, mark files Keep/Move, click "Download decisions",')
        print(f"save it as:\n  {config.decisions_file}\nthen run this script again.\n")

        if input("Move ALL non-keeper duplicates now instead? [Y/N]: ").strip().lower() in _YES:
            _do_move(non_keeper_paths(groups), config)
        else:
            print("\nNo files were moved.")
        return

    decisions = load_decisions(decisions_path, config)
    if not decisions:
        print(f"No usable decisions in:\n  {decisions_path}\nNo files were moved.")
        return

    to_move, kept_groups, warnings = resolve_moves(groups, decisions)

    for warning in warnings:
        print(f"  ! {warning}")
    if warnings:
        print()

    print(f"Decisions file:     {decisions_path}")
    print(f"Files to move:      {len(to_move)}")
    print(f"Groups kept intact: {kept_groups}\n")

    if not to_move:
        print("Nothing is marked for moving. No files were moved.")
        return

    if input(f"Move {len(to_move)} file(s) to the _duplicates folder? [Y/N]: ").strip().lower() in _YES:
        _do_move(to_move, config)
    else:
        print("\nNo files were moved.")


def _run_analysis(config: Config, apply_decisions: bool = True) -> None:
    """Full pipeline: scan, analyze, group, write the HTML review page.

    ``apply_decisions`` is turned off when the user has just declined an
    existing decisions file - that file is now stale, so we regenerate the
    report and let them review it again rather than applying it.
    """
    print("Scanning files...")
    files = scan_files(config)
    print(f"Found {len(files)} image files.\n")

    print("Analyzing images...")
    images = analyze(files)
    print(f"\nSuccessfully analyzed {len(images)} images.\n")

    print("Searching for visual duplicates...")
    groups = find_duplicate_groups(images, config)
    total_duplicates = sum(len(group) - 1 for group in groups)
    print(f"\nFound {len(groups)} duplicate groups.")
    print(f"Found {total_duplicates} duplicate files.\n")

    print("Building HTML review page...")
    write_report(groups, config)
    print(f"\nReview page saved to:\n  {config.report_file}")

    if not groups:
        print("\nNo duplicates found.")
        return

    if not apply_decisions:
        print()
        print("Open the review page, mark files Keep/Move, click \"Download decisions\",")
        print(f"save it as:\n  {config.decisions_file}\nthen run this script again to move them.")
        return

    print()
    _banner("DUPLICATE MOVING")
    print()
    _apply_decisions(groups, config)


def run(config: Config) -> None:
    _banner("PHOTO DUPLICATE FINDER")
    print()
    print(f"Source directory:\n  {config.source_dir}")
    print(f"\nDuplicates directory:\n  {config.duplicates_dir}")
    print(f"\nReview page:\n  {config.report_file}")
    print(f"\nHash distance: {config.hash_distance}\n")

    if not config.source_dir.exists():
        print("ERROR: Source directory does not exist.")
        return

    # Direction 1: a decisions file is already there -> just move what it marks.
    decisions_path = find_decisions_file(config)
    if decisions_path is not None:
        _banner("EXISTING DECISIONS FOUND")
        print()
        print(f"Decisions file:\n  {decisions_path}\n")
        answer = input(
            "Move the duplicate files marked in this file now? [Y/N]: "
        ).strip().lower()

        if answer in _YES:
            print()
            _banner("DUPLICATE MOVING")
            print()
            _move_from_decisions(decisions_path, config)
            return

        print("\nRunning a fresh analysis instead...\n")
        print()
        _banner("ANALYSIS")
        print()
        _run_analysis(config, apply_decisions=False)
        return

    # Direction 2: no decisions file at all -> analyze from scratch.
    print()
    _banner("ANALYSIS")
    print()
    _run_analysis(config)
