"""Read the Keep/Move decisions exported from the review page and apply them."""

import json
from pathlib import Path

from .config import Config
from .grouping import Group

# normalized-path -> "keep" | "move"
Decisions = dict[str, str]


def find_decisions_file(config: Config) -> Path | None:
    candidates = [config.decisions_file, Path.cwd() / config.decisions_file.name]

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if candidate.exists():
            return candidate

    return None


def load_decisions(path: Path, config: Config) -> Decisions:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"\nERROR reading decisions file:\n  {path}\n  {e}")
        return {}

    if not isinstance(data, dict):
        return {}

    raw = data.get("decisions", data)
    source = data.get("source")
    if source and Path(source) != config.source_dir:
        print("  ! decisions file was generated for a different source:")
        print(f"    {source}")

    decisions: Decisions = {}
    for key, value in raw.items():
        choice = str(value).strip().lower()
        if choice in ("keep", "move"):
            decisions[str(Path(key))] = choice  # normalizes slash direction

    return decisions


def resolve_moves(
    groups: list[Group], decisions: Decisions
) -> tuple[list[Path], int, list[str]]:
    """
    Turn the decision map into a concrete move list.

    Returns (paths_to_move, groups_left_intact, warnings). A group where every
    file is marked Move is refused for safety.
    """
    to_move: list[Path] = []
    kept_groups = 0
    warnings: list[str] = []

    for number, group in enumerate(groups, 1):
        marks = [(info, decisions.get(str(info.path), "keep")) for info in group]
        movers = [info for info, choice in marks if choice == "move"]
        keepers = [info for info, choice in marks if choice != "move"]
        undecided = [info for info in group if str(info.path) not in decisions]

        if undecided:
            warnings.append(f"Group {number}: {len(undecided)} file(s) had no decision - kept.")

        if not keepers:
            warnings.append(f"Group {number}: every file marked MOVE - skipped for safety.")
            continue

        if not movers:
            kept_groups += 1
            continue

        to_move.extend(info.path for info in movers)

    return to_move, kept_groups, warnings
