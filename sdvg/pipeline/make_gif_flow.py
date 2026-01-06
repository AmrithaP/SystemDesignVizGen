from sdvg.pipeline.render_diagram import render_architecture_spec

from pathlib import Path
import shutil
from PIL import Image

def spec_to_gif_edge_flow(
    spec,
    out_base: str,
    direction: str = "TB",
    frames: int = 18,
    window: int = 3,
    duration_ms: int = 120,
    keep_frames: bool = False,   # 👈 NEW FLAG
):
    out_base = Path(out_base)
    out_dir = out_base.parent
    frames_dir = out_dir / f"{out_base.stem}_frames"

    frames_dir.mkdir(parents=True, exist_ok=True)

    edges = [
        (r["from_id"], r["to_id"])
        for r in spec.get("relationships", [])
        if r.get("from_id") and r.get("to_id")
    ]

    frame_paths = []

    for i in range(frames):
        start = i % len(edges)
        highlight = set(
            edges[(start + k) % len(edges)]
            for k in range(min(window, len(edges)))
        )

        frame_path = frames_dir / f"frame_{i:03d}.png"

        render_architecture_spec(
            spec,
            out_path_no_ext=str(frame_path.with_suffix("")),
            fmt="png",
            direction=direction,
            show_edge_labels=False,
            highlight_edges=highlight,
        )

        frame_paths.append(frame_path)

    # --- stitch GIF ---
    images = [Image.open(p).convert("RGBA") for p in frame_paths]

    # normalize canvas size (prevents jitter)
    max_w = max(im.width for im in images)
    max_h = max(im.height for im in images)

    fixed = []
    for im in images:
        canvas = Image.new("RGBA", (max_w, max_h), (255, 255, 255, 255))
        canvas.paste(
            im,
            ((max_w - im.width) // 2, (max_h - im.height) // 2),
        )
        fixed.append(canvas)

    gif_path = out_base.with_suffix(".gif")
    fixed[0].save(
        gif_path,
        save_all=True,
        append_images=fixed[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
    )

    # 🧹 cleanup frames unless requested
    if not keep_frames:
        shutil.rmtree(frames_dir)

    return str(gif_path)
