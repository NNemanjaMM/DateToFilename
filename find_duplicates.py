"""Find visually-duplicate photos, review them in an HTML page, move the ones you mark.

The script runs one of two ways depending on whether a decisions file exists:

  * _duplicate_decisions.json IS present next to the source folder
      -> it asks "Move the marked files now? [Y/N]".
         Y  = move exactly what the file marks "move", then finish.
         N  = fall through to a fresh analysis (below).

  * _duplicate_decisions.json is NOT present (or you answered N)
      -> a full analysis runs and rebuilds _duplicate_report.html.
         Open it, mark each file Keep / Move, click "Download decisions",
         drop _duplicate_decisions.json next to the source folder, and run
         the script again to move what you marked.

The implementation lives in the `dupfinder` package next to this file.
"""

from pathlib import Path

from dupfinder import Config
from dupfinder.cli import run

CONFIG = Config(
    source_dir=Path(r"D:\Users\family\Desktop\todo"),
    hash_distance=0,        # 0 = identical, 1-3 = very similar, 4-5 = more tolerant
    embed_thumbnails=True,  # False = sidecar _duplicate_report_assets/ folder
)


if __name__ == "__main__":
    run(CONFIG)
