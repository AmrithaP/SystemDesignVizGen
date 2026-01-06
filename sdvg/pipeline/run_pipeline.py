from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from sdvg.pipeline.discover_links import discover_links
from sdvg.pipeline.scrape import scrape_url, PageContent
from sdvg.pipeline.extract_spec import extract_spec
from sdvg.pipeline.render_diagram import render_architecture_spec

# If you want GIF generation:
# - If you're using png_to_gif_pulse:
from sdvg.pipeline.make_gif import png_to_gif_pulse

# - If you're using spec_to_gif_edge_flow:
# from sdvg.pipeline.make_gif_flow import spec_to_gif_edge_flow


@dataclass
class PipelineResult:
    run_id: str
    topic: str
    level: str
    links: List[str]
    scraped: int
    png_path: str
    gif_path: Optional[str] = None


def _safe_slug(s: str) -> str:
    return (s or "").strip().lower().replace(" ", "_")


def run_pipeline(
    topic: str,
    level: str,
    *,
    max_links: int = 5,
    show_edge_labels: bool = True,
    direction: str = "TB",
    make_gif: bool = True,
    out_dir: str = "out",
    keep_frames: bool = False,  # for flow-gif mode (optional)
) -> PipelineResult:
    """
    End-to-end: discover -> scrape -> extract -> render -> (optional gif)
    Returns paths of output assets.
    """

    topic = (topic or "").strip()
    level = (level or "").strip().upper()
    if level not in {"HLD", "LLD"}:
        raise ValueError("level must be HLD or LLD")

    os.makedirs(out_dir, exist_ok=True)

    run_id = uuid.uuid4().hex[:10]
    safe_topic = _safe_slug(topic)
    safe_level = _safe_slug(level)
    out_base = os.path.join(out_dir, f"{safe_topic}_{safe_level}_{run_id}")

    # 1) Discover links
    links = discover_links(topic, level, max_links=max_links)

    # 2) Scrape pages (skip failures)
    pages: List[PageContent] = []
    for url in links:
        try:
            pages.append(scrape_url(url))
        except Exception as e:
            print(f"[scrape skipped] {url} -> {type(e).__name__}: {e}")

    if not pages:
        raise RuntimeError("No pages could be scraped. Try different links or relax blockers.")

    # 3) Extract spec
    spec = extract_spec(topic, level, pages)

    # 4) Render PNG
    png_path = render_architecture_spec(
        spec,
        out_path_no_ext=out_base,
        direction=direction,
        show_edge_labels=show_edge_labels,
    )

    gif_path = None

    # 5) GIF (choose ONE approach)
    if make_gif:
        # Option A: simple pulse/fade gif from final PNG
        gif_path = png_to_gif_pulse(
            png_path=png_path,
            gif_path=out_base + ".gif",
            duration_ms=140,
            add_fade_in=True,
        )

        # Option B: edge-flow gif (if you're using make_gif_flow.py)
        # gif_path = spec_to_gif_edge_flow(
        #     spec=spec,
        #     out_gif_path=out_base + ".gif",
        #     out_dir=out_dir,
        #     direction=direction,
        #     show_edge_labels=show_edge_labels,
        #     keep_frames=keep_frames,
        # )

    return PipelineResult(
        run_id=run_id,
        topic=topic,
        level=level,
        links=links,
        scraped=len(pages),
        png_path=png_path,
        gif_path=gif_path,
    )
