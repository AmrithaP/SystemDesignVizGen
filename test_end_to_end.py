from sdvg.pipeline.run_pipeline import run_pipeline

topic = "UBER"
level = "HLD"

res = run_pipeline(
    topic=topic,
    level=level,
    max_links=5,
    show_edge_labels=True,
    direction="TB",
    make_gif=True,
)

print("Run ID:", res.run_id)
print("Links:", res.links)
print("Scraped pages:", res.scraped)
print("PNG:", res.png_path)
print("GIF:", res.gif_path)


"""from sdvg.pipeline.discover_links import discover_links
from sdvg.pipeline.scrape import scrape_url
from sdvg.pipeline.extract_spec import extract_spec
from sdvg.pipeline.render_diagram import render_architecture_spec
#from sdvg.pipeline.make_gif import png_to_gif_pulse
from sdvg.pipeline.make_gif_flow import spec_to_gif_edge_flow

import os

topic = "UBER"
level = "HLD"

# 1) Discover links
links = discover_links(topic, level, max_links=5)
print("Links:", links)

# 2) Scrape pages
pages = []
for url in links:
    try:
        pages.append(scrape_url(url))
    except Exception as e:
        print(f"[scrape skipped] {url} -> {type(e).__name__}: {e}")

# optional: fail fast if nothing scraped
if not pages:
    raise RuntimeError("No pages could be scraped. Try different links or relax blockers.")

# 3) Extract architecture spec (Gemini)
spec = extract_spec(topic, level, pages)

# 4) Render diagram
os.makedirs("out", exist_ok=True)

safe_topic = topic.strip().lower().replace(" ", "_")
safe_level = level.strip().lower()
out_base = f"out/{safe_topic}_{safe_level}"

out_img = render_architecture_spec(
    spec,
    out_path_no_ext=out_base,
    direction="TB",
    show_edge_labels=True
)

# 5) Make GIF (no hardcode)
out_gif = spec_to_gif_edge_flow(
    spec=spec,
    out_base=out_base,
    direction="TB",
    frames=18,
    window=3,
    duration_ms=120,
    keep_frames=False,   # 👈 auto-delete frames
)

print("Rendered diagram:", out_img)
print("Rendered gif:", out_gif)
"""