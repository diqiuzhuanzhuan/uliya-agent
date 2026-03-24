import json
from typing import Any


def sse_pack(event: str, data: dict[str, Any]) -> str:
    """Format a payload as a Server-Sent Events frame."""

    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
