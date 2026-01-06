from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from sdvg.pipeline.run_pipeline import run_pipeline

OUT_DIR = "out"

app = FastAPI(title="SDVG API")

# allow local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# serve output files
os.makedirs(OUT_DIR, exist_ok=True)
app.mount("/out", StaticFiles(directory=OUT_DIR), name="out")


class GenerateRequest(BaseModel):
    topic: str
    level: str = "HLD"
    max_links: int = 5
    show_edge_labels: bool = True
    direction: str = "TB"
    make_gif: bool = True


@app.post("/api/generate")
def generate(req: GenerateRequest):
    res = run_pipeline(
        topic=req.topic,
        level=req.level,
        max_links=req.max_links,
        show_edge_labels=req.show_edge_labels,
        direction=req.direction,
        make_gif=req.make_gif,
        out_dir=OUT_DIR,
    )

    # return URLs the frontend can load
    png_name = os.path.basename(res.png_path)
    gif_name = os.path.basename(res.gif_path) if res.gif_path else None

    return {
        "run_id": res.run_id,
        "topic": res.topic,
        "level": res.level,
        "links": res.links,
        "scraped": res.scraped,
        "png_url": f"/out/{png_name}",
        "gif_url": f"/out/{gif_name}" if gif_name else None,
    }
