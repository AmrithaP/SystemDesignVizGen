# sdvg/pipeline/render_diagram.py
from __future__ import annotations

from typing import Dict, Any, List
from graphviz import Digraph


TYPE_STYLE = {
    # type: (shape, extra_attrs)
    "client application": ("box", {"style": "rounded,filled"}),
    "application": ("box", {"style": "rounded,filled"}),
    "client": ("box", {"style": "rounded,filled"}),

    "gateway": ("diamond", {"style": "filled"}),
    "api gateway": ("diamond", {"style": "filled"}),

    "core service": ("box", {"style": "filled"}),
    "service": ("box", {"style": "filled"}),

    "database": ("cylinder", {"style": "filled"}),
    "data store": ("cylinder", {"style": "filled"}),

    "cache": ("component", {"style": "filled"}),
    "cache/queue": ("component", {"style": "filled"}),
    "messaging system": ("component", {"style": "filled"}),

    "security": ("octagon", {"style": "filled"}),
    "infrastructure": ("box3d", {"style": "filled"}),

    "third-party service": ("oval", {"style": "filled"}),
    "external service": ("oval", {"style": "filled"}),

    # fallback handled below
}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


# ---------- layout helpers ----------
CLIENT_TYPES = {"client application", "application", "client"}
EDGE_TYPES = {"gateway", "api gateway", "infrastructure", "security"}  # edge/security-ish
CORE_TYPES = {"core service", "service"}
DATA_TYPES = {"database", "data store", "cache", "cache/queue", "messaging system"}
EXTERNAL_TYPES = {"third-party service", "external service"}


def _bucket_for_type(t: str) -> str:
    t = _norm(t)
    if t in CLIENT_TYPES:
        return "client"
    if t in DATA_TYPES:
        return "data"
    if t in EXTERNAL_TYPES:
        return "external"
    if t in CORE_TYPES:
        return "core"
    if t in EDGE_TYPES:
        # separate security vs edge infra for nicer grouping
        if t == "security":
            return "security"
        return "edge"
    return "core"  # sensible default


def _short_edge_label(label: str) -> str:
    """Keep labels tiny; long labels destroy diagram readability."""
    if not label:
        return ""

    s = label.strip().lower()

    # common phrases -> short verbs
    replacements = [
        ("sends requests to", "calls"),
        ("routes requests to", "routes"),
        ("routes traffic to", "routes"),
        ("forwards traffic to", "forwards"),
        ("forwards requests to", "forwards"),
        ("forwards data to", "streams"),
        ("publishes events to", "pub"),
        ("streams data to", "streams"),
        ("stores data in", "writes"),
        ("stores state in", "writes"),
        ("persists data to", "writes"),
        ("reads from", "reads"),
        ("uses data from", "uses"),
        ("integrates with", "integrates"),
        ("requests calculation from", "calls"),
        ("provides data for", "feeds"),
        ("feeds data to", "feeds"),
        ("informs", "informs"),
        ("updates", "updates"),
        ("queries", "queries"),
        ("returns", "returns"),
        ("uses", "uses"),
    ]
    for a, b in replacements:
        if s == a:
            return b

    # if it’s long, truncate
    if len(label) > 18:
        return label[:18].rstrip() + "…"
    return label

def _edge_style(relation: str, from_type: str, to_type: str) -> dict:
    """
    Decide edge style based on relationship semantics.
    """
    r = (relation or "").lower()
    ft = (from_type or "").lower()
    tt = (to_type or "").lower()

    # async / event / stream / notify
    if any(k in r for k in [
        "stream", "publish", "event", "notify", "push", "feeds", "logs"
    ]):
        return {"style": "dotted"}

    # analytics / ml feedback loops
    if "ml" in ft or "ml" in tt or "analytics" in ft or "analytics" in tt:
        return {"style": "dotted"}

    # external integrations
    if "external" in tt or "third-party" in tt:
        return {"style": "dotted"}

    # default = solid
    return {"style": "solid"}

def _is_core_edge(r: dict) -> bool:
    rel = (r.get("relation") or "").lower()
    label = (r.get("label") or "").lower()

    # always keep main request flow
    if any(k in rel or k in label for k in [
        "routes", "calls", "requests", "matches"
    ]):
        return True

    # hide noisy background edges in HLD
    if any(k in rel or k in label for k in [
        "logs", "feeds", "streams", "analytics", "ml", "warehouse"
    ]):
        return False

    return True



def render_architecture_spec(
    spec: Dict[str, Any],
    out_path_no_ext: str = "out/diagram",
    fmt: str = "png",
    direction: str = "TB",
    show_edge_labels: bool = False,
    highlight_edges: set[tuple[str, str]] | None = None,   # ✅ ADD THIS
) -> str:

    """
    Renders spec -> image using Graphviz.
    Returns the final output file path (e.g., out/diagram.png).
    """

    topic = spec.get("topic", "").upper()
    level = spec.get("level", "")
    title = f"{topic} — {level} Architecture" if topic or level else "Architecture"

    g = Digraph(comment=f"{spec.get('topic','')} {spec.get('level','')}", engine="dot")

    # ---- global graph settings (spacing + title) ----
    g.attr(
    graph=(
        'pad="0.4", nodesep="0.60", ranksep="1.05", '
        'splines="ortho", overlap="false", concentrate="true", '
        'newrank="true"'
    )
    )
    g.attr(rankdir=direction)

    # Title at top
    g.attr(label=title, labelloc="t", fontsize="18")

    # Defaults
    g.attr("node", fontsize="11", margin="0.18,0.10")
    g.attr("edge", fontsize="9", arrowsize="0.6", penwidth="1")


    # 1) nodes bucketed into clusters
    comp_by_id: Dict[str, Dict[str, Any]] = {}
    buckets: Dict[str, List[str]] = {
        "client": [],
        "edge": [],
        "security": [],
        "core": [],
        "data": [],
        "external": [],
    }

    for c in spec.get("components", []):
        cid = c["id"]
        comp_by_id[cid] = c
        buckets[_bucket_for_type(c.get("type", ""))].append(cid)

    # cluster definitions
    cluster_meta = [
        ("client", "Client Layer"),
        ("edge", "Edge Layer"),
        ("security", "Security & Observability"),
        ("core", "Core Services"),
        ("data", "Data Stores"),
        ("external", "External Providers"),
    ]

    def add_node_to_graph(graph: Digraph, cid: str):
        c = comp_by_id[cid]
        name = c.get("name", cid)
        ctype = _norm(c.get("type", ""))

        shape, extra = TYPE_STYLE.get(ctype, ("box", {"style": "rounded"}))
        attrs = {"shape": shape}
        attrs.update(extra)

        # cleaner label: name + optional type
        t = c.get("type", "")
        attrs["label"] = f"{name}\n({t})" if t else name

        graph.node(cid, **attrs)

    for bucket_key, bucket_title in cluster_meta:
        ids = buckets.get(bucket_key, [])
        if not ids:
            continue

        with g.subgraph(name=f"cluster_{bucket_key}") as csub:
            csub.attr(label=bucket_title, style="rounded", fontsize="13")
            # Keeping clusters visually separated helps a lot
            csub.attr("graph", margin="12")

            for cid in ids:
                add_node_to_graph(csub, cid)

    # 2) edges (cleaner)
    highlight_edges = highlight_edges or set()

    for r in spec.get("relationships", []):
        if spec.get("level") == "HLD" and not _is_core_edge(r):
            continue

        a = r.get("from_id")
        b = r.get("to_id")
        if a not in comp_by_id or b not in comp_by_id:
            continue

        raw_label = (r.get("label") or r.get("relation") or "").strip()
        label = _short_edge_label(raw_label) if show_edge_labels else ""

        from_type = comp_by_id[a].get("type", "")
        to_type = comp_by_id[b].get("type", "")

        style_attrs = _edge_style(r.get("relation", ""), from_type, to_type)

        # ✅ highlight selected edges
        if (a, b) in highlight_edges:
            style_attrs = {**style_attrs, "penwidth": "3", "color": "black"}
        else:
            style_attrs = {**style_attrs, "penwidth": "1", "color": "gray35"}

        if label:
            g.edge(a, b, label=label, **style_attrs)
        else:
            g.edge(a, b, **style_attrs)


    # 3) render
    out_file = g.render(filename=out_path_no_ext, format=fmt, cleanup=True)
    return out_file
