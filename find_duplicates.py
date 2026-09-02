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
    hash_distance=6,        # pass-1 net: how far the perceptual hash may drift.
                            # A downscaled + re-compressed copy of the same photo
                            # drifts ~2 bits for a mild shrink, 4-6 for an
                            # aggressive one, so 0 misses them entirely. Keep
                            # this loose - the pixel check rejects false hits.
    pixel_check=True,        # pass 2: re-check each candidate group pixel-by-pixel
                            # and split/drop images that are not really alike.
                            # It can only remove matches, never add them.
    pixel_similarity=0.90,  # SSIM >= this = same photo. 0.90 is fairly strict;
                            # lower (0.85) to tolerate stronger re-compression,
                            # raise (0.93) to reject near-miss burst frames.
    pixel_size=128,         # pass 2 compares images as pixel_size x pixel_size.
                            # Larger (192-256) is stricter and slower; smaller
                            # (96) is faster and more forgiving of blur.
    embed_thumbnails=True,  # False = sidecar _duplicate_report_assets/ folder
)


if __name__ == "__main__":
    run(CONFIG)
