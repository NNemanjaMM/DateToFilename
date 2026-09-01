"""Build the HTML review page from assets/report.html (CSS inline) and report.js."""

import base64
import html
import io
import json
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps

from .config import Config
from .grouping import Group, sort_by_quality
from .model import ImageInfo

_ASSETS = Path(__file__).resolve().parent / "assets"


def _fill(template: str, **parts: str) -> str:
    """Replace {{name}} placeholders. `body` is filled last so its content is
    never rescanned for placeholders."""
    for key, value in parts.items():
        template = template.replace("{{" + key + "}}", value)
    return template


def _format_size(n: int) -> str:
    if n < 1024 * 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n / 1024 / 1024:.2f} MB"


# ---- Thumbnails ----

def _thumbnail_bytes(path: Path, max_px: int) -> bytes | None:
    try:
        with Image.open(path) as image:
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_px, max_px))
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=75)
            return buffer.getvalue()
    except Exception as e:
        print(f"\nERROR building preview:\n  {path}\n  {e}")
        return None


def _thumbnail_src(path: Path, group_number: int, position: int, config: Config) -> str | None:
    data = _thumbnail_bytes(path, config.thumbnail_max_px)
    if data is None:
        return None

    if config.embed_thumbnails:
        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")

    config.assets_dir.mkdir(parents=True, exist_ok=True)
    name = f"group{group_number:03d}_{position}.jpg"
    (config.assets_dir / name).write_bytes(data)
    return f"{config.assets_dir.name}/{name}"


# ---- Per-group HTML (data-driven, so it stays in code) ----

def _describe(info: ImageInfo, keeper: ImageInfo) -> dict:
    return {
        "name": info.path.name,
        "path": str(info.path),
        "folder": str(info.path.parent),
        "uri": info.path.as_uri(),
        "resolution": f"{info.width} x {info.height}",
        "mp": f"{info.pixels / 1_000_000:.1f} MP",
        "size": _format_size(info.file_size),
        "format": info.image_format or "?",
        "hash": str(info.phash),
        "distance": info.distance_to(keeper),
        "pixels": info.pixels,
        "bytes": info.file_size,
    }


def _render_card(desc: dict, is_keeper: bool, thumb_src: str | None) -> str:
    badge = ('<span class="badge keep">suggested keep</span>' if is_keeper
             else '<span class="badge dup">duplicate</span>')
    inner = (f'<img loading="lazy" alt="" src="{thumb_src}">' if thumb_src
             else '<div class="noimg">no preview</div>')
    decision = "keep" if is_keeper else "move"

    return (
        f'<figure class="{"card keep" if is_keeper else "card"}" '
        f'data-path="{html.escape(desc["path"])}" data-decision="{decision}">'
        f'<a href="{html.escape(desc["uri"])}" target="_blank" rel="noopener">{inner}</a>'
        f'<figcaption>{badge}'
        f'<div class="name">{html.escape(desc["name"])}</div>'
        f'<div class="path">{html.escape(desc["path"])}</div>'
        f'<div class="decide" role="group" aria-label="decision">'
        f'<button type="button" data-set="keep">Keep</button>'
        f'<button type="button" data-set="move">Move</button>'
        f'</div></figcaption></figure>'
    )


def _metric_row(label, descs, field, key=None, mono=False) -> str:
    keep_val = key(descs[0]) if key else None
    cells = [f"<th>{html.escape(label)}</th>"]

    for i, desc in enumerate(descs):
        classes = ["mono"] if mono else []
        if key and i > 0:
            value = key(desc)
            if value < keep_val:
                classes.append("worse")
            elif value > keep_val:
                classes.append("better")
        attr = f' class="{" ".join(classes)}"' if classes else ""
        cells.append(f'<td{attr}>{html.escape(str(desc[field]))}</td>')

    return "<tr>" + "".join(cells) + "</tr>"


def _render_group(number: int, group: Group, config: Config) -> str:
    keeper = group[0]
    descs = [_describe(info, keeper) for info in group]

    cards = "".join(
        _render_card(desc, i == 0, _thumbnail_src(group[i].path, number, i, config))
        for i, desc in enumerate(descs)
    )

    header_cells = ["<th></th>"]
    for i, desc in enumerate(descs):
        header_cells.append(f'<th>{html.escape(("KEEP - " if i == 0 else "") + desc["name"])}</th>')

    rows = [
        _metric_row("Resolution", descs, "resolution", key=lambda d: d["pixels"]),
        _metric_row("Megapixels", descs, "mp", key=lambda d: d["pixels"]),
        _metric_row("File size", descs, "size", key=lambda d: d["bytes"]),
        _metric_row("Format", descs, "format"),
        _metric_row("Perceptual hash", descs, "hash", mono=True),
    ]

    distance_cells = ["<th>Distance to keeper</th>"]
    for i, desc in enumerate(descs):
        distance_cells.append("<td>&mdash;</td>" if i == 0 else f'<td>{desc["distance"]}</td>')
    rows.append("<tr>" + "".join(distance_cells) + "</tr>")

    rows.append(_metric_row("Folder", descs, "folder", mono=True))

    table = (
        '<table class="cmp"><thead><tr>'
        + "".join(header_cells)
        + "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )

    return (
        f'<section class="group" id="group-{number}" data-group="{number}">'
        f'<h2>Group {number} <span class="count">&middot; {len(group)} files</span>'
        f'<span class="gactions">'
        f'<button type="button" data-g="keepall">Keep all</button> '
        f'<button type="button" data-g="reset">Reset</button>'
        f'</span></h2>'
        f'<p class="invalidnote">Every file here is marked Move - this group is skipped '
        f'until at least one file is set to Keep.</p>'
        f'<div class="cards row">{cards}</div>'
        f'{table}</section>\n'
    )


# ---- Whole page ----

def write_report(groups: list[Group], config: Config) -> None:
    total_duplicates = sum(len(group) - 1 for group in groups)

    if not config.embed_thumbnails:
        shutil.rmtree(config.assets_dir, ignore_errors=True)

    sections: list[str] = []
    nav: list[str] = []
    for number, group in enumerate(groups, 1):
        sort_by_quality(group)
        sections.append(_render_group(number, group, config))
        nav.append(f'<a href="#group-{number}">{number}</a>')

    generated = datetime.now().strftime("%Y-%m-%d %H:%M")

    meta = json.dumps({
        "source": str(config.source_dir),
        "generated": generated,
        "hash_distance": config.hash_distance,
    }).replace("<", "\\u003c")

    summary = (
        f'Source: <code>{html.escape(str(config.source_dir))}</code> &middot; '
        f'hash distance {config.hash_distance} &middot; {len(groups)} groups &middot; '
        f'{total_duplicates} duplicate files &middot; generated {generated}'
    )

    body = "".join(sections) or '<div class="group">No duplicate groups detected.</div>'

    doc = _fill(
        (_ASSETS / "report.html").read_text(encoding="utf-8"),
        title=html.escape(config.source_dir.name),
        js=(_ASSETS / "report.js").read_text(encoding="utf-8"),
        meta=meta,
        summary=summary,
        nav="".join(nav),
        body=body,
    )

    config.report_file.write_text(doc, encoding="utf-8")
