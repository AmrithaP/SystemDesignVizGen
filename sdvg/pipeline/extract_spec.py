from __future__ import annotations
import time
import random

import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass

from dotenv import load_dotenv
from google import genai

from sdvg.pipeline.scrape import PageContent

load_dotenv()


# ---------- JSON Schema (Structured Outputs) ----------
SPEC_SCHEMA: Dict[str, Any] = {
    "name": "sdvg_architecture_spec",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "topic": {"type": "string"},
            "level": {"type": "string", "enum": ["HLD", "LLD"]},
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "type": {"type": "string"},
                        "description": {"type": "string"},
                        "source_urls": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["id", "name", "type", "description", "source_urls"]
                }
            },
            "relationships": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "from_id": {"type": "string"},
                        "to_id": {"type": "string"},
                        "relation": {"type": "string"},
                        "label": {"type": "string"},
                        "source_urls": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["from_id", "to_id", "relation", "label", "source_urls"]
                }
            }
        },
        "required": ["topic", "level", "components", "relationships"]
    }
}


def _build_prompt(topic: str, level: str, pages: List[PageContent]) -> str:
    chunks = []
    for p in pages[:3]:
        img_lines = "\n".join([f"- {img.src} (score={img.score})" for img in p.images[:5]])
        chunks.append(
            f"URL: {p.url}\n"
            f"TITLE: {p.title or ''}\n"
            f"TOP_IMAGES:\n{img_lines}\n"
             f"TEXT:\n{p.text[:5000]}\n" #f"TEXT:\n{p.text}\n"
        )

    joined = "\n\n---\n\n".join(chunks)

    return (
        "You are extracting a system design architecture spec.\n"
        f"Topic: {topic}\n"
        f"Level: {level}\n\n"
        "Return ONLY valid JSON that matches this schema exactly:\n"
        f"{json.dumps(SPEC_SCHEMA['schema'])}\n\n"
        "Rules:\n"
        "- Only include components that are clearly supported by the sources.\n"
        "- Prefer generic reusable names (API Gateway, Matching Service, etc.).\n"
        "- Component ids must be stable snake_case (api_gateway, matching_service).\n"
        "- Relationships must reference component ids.\n"
        "- Put supporting URL(s) in source_urls for each component/relationship.\n"
        "- If sources disagree, keep the common core.\n\n"
        f"SOURCES:\n{joined}"
    )

def enforce_grounding(spec: dict, pages: list) -> dict:
    allowed = {p.url.rstrip("/") for p in pages}

    def keep_allowed(urls):
        return [u for u in (urls or []) if u.rstrip("/") in allowed]

    # filter component sources
    grounded_components = []
    for c in spec.get("components", []):
        c["source_urls"] = keep_allowed(c.get("source_urls"))
        if c["source_urls"]:  # keep only if grounded
            grounded_components.append(c)

    # filter relationship sources + drop edges referencing removed components
    kept_ids = {c["id"] for c in grounded_components}
    grounded_relationships = []
    for r in spec.get("relationships", []):
        r["source_urls"] = keep_allowed(r.get("source_urls"))
        if (
            r["source_urls"]
            and r.get("from_id") in kept_ids
            and r.get("to_id") in kept_ids
        ):
            grounded_relationships.append(r)

    spec["components"] = grounded_components
    spec["relationships"] = grounded_relationships
    return spec


def extract_spec(
    topic: str,
    level: str,
    pages: List[PageContent],
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
    """
    Returns a validated JSON object with components + relationships.
    Requires GEMINI_API_KEY in env.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY. Put it in .env and restart your terminal.")

    client = genai.Client(api_key=api_key)

    prompt = _build_prompt(topic, level, pages)

    # --- Gemini call with retries + longer timeout ---
    last_err = None
    for attempt in range(4):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "temperature": 0.1,
                },
            )
            break
        except Exception as e:
            last_err = e
            time.sleep((2 ** attempt) + random.random())
    else:
        raise last_err



    text = resp.text.strip()

    # Gemini sometimes wraps JSON in ```json ... ```
    if text.startswith("```"):
        # remove first line ``` or ```json
        text = "\n".join(text.splitlines()[1:])
        # drop trailing ```
        if text.strip().endswith("```"):
            text = text.strip()[:-3].strip()


    #return json.loads(text)
    spec = json.loads(text)
    spec = enforce_grounding(spec, pages)
    for k in ["topic", "level", "components", "relationships"]:
        if k not in spec:
            raise ValueError(f"Missing key in model output: {k}")
    
    return spec

