# sdvg/knowledge/components.py
from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ComponentStyle:
    shape: str          # e.g., "box", "cylinder", "ellipse"
    icon: str           # optional key (later you can map to SVG icons)
    fill: str           # color name or hex (renderer decides)
    border: str
    text: str


# Canonical component types (expand over time)
COMPONENT_TYPES: Dict[str, ComponentStyle] = {
    "CLIENT": ComponentStyle(shape="box",      icon="client",   fill="#E8F0FE", border="#1A73E8", text="#0B1F3A"),
    "API_GATEWAY": ComponentStyle(shape="box", icon="gateway",  fill="#FFF4E5", border="#FB8C00", text="#3A1A00"),
    "LOAD_BALANCER": ComponentStyle(shape="box", icon="lb",     fill="#FFF4E5", border="#FB8C00", text="#3A1A00"),
    "SERVICE": ComponentStyle(shape="box",     icon="service",  fill="#E8F5E9", border="#2E7D32", text="#0B2A14"),
    "DB_REL": ComponentStyle(shape="cylinder", icon="db",       fill="#F3E5F5", border="#6A1B9A", text="#2A0B3A"),
    "DB_NOSQL": ComponentStyle(shape="cylinder",icon="nosql",   fill="#F3E5F5", border="#6A1B9A", text="#2A0B3A"),
    "CACHE": ComponentStyle(shape="box",       icon="cache",    fill="#E0F7FA", border="#00838F", text="#00363A"),
    "QUEUE": ComponentStyle(shape="box",       icon="queue",    fill="#FFFDE7", border="#F9A825", text="#3A2A00"),
    "OBJECT_STORE": ComponentStyle(shape="box",icon="bucket",   fill="#E1F5FE", border="#0277BD", text="#0B223A"),
    "CDN": ComponentStyle(shape="box",         icon="cdn",      fill="#E1F5FE", border="#0277BD", text="#0B223A"),
    "MONITORING": ComponentStyle(shape="box",  icon="metrics",  fill="#ECEFF1", border="#455A64", text="#102027"),
}


# Synonyms → canonical types (this is your “mapping brain”)
TYPE_SYNONYMS: Dict[str, str] = {
    # clients
    "mobile app": "CLIENT",
    "rider app": "CLIENT",
    "driver app": "CLIENT",
    "web app": "CLIENT",

    # gateways / networking
    "api gateway": "API_GATEWAY",
    "gateway": "API_GATEWAY",
    "load balancer": "LOAD_BALANCER",
    "lb": "LOAD_BALANCER",

    # storage
    "postgres": "DB_REL",
    "mysql": "DB_REL",
    "sql": "DB_REL",
    "cassandra": "DB_NOSQL",
    "dynamodb": "DB_NOSQL",
    "mongodb": "DB_NOSQL",

    # caching / queues
    "redis": "CACHE",
    "memcached": "CACHE",
    "kafka": "QUEUE",
    "rabbitmq": "QUEUE",
    "sqs": "QUEUE",

    # compute
    "service": "SERVICE",
    "microservice": "SERVICE",
}
