# sdvg/knowledge/relationships.py
from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EdgeStyle:
    line: str       # "solid" or "dashed"
    arrow: str      # "normal" (later: open/vee)
    label: str      # default label


EDGE_TYPES: Dict[str, EdgeStyle] = {
    "SYNC_CALL": EdgeStyle(line="solid",  arrow="normal", label="sync"),
    "ASYNC_EVENT": EdgeStyle(line="dashed", arrow="normal", label="async"),
    "READ": EdgeStyle(line="solid", arrow="normal", label="read"),
    "WRITE": EdgeStyle(line="solid", arrow="normal", label="write"),
}
