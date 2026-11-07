import json
import logging
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Format operational logs as one JSON object per line."""

    structured_fields = (
        "event",
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "user_id",
        "workspace_id",
        "role",
        "outcome",
        "reason",
        "result_count",
        "limit",
        "offset",
    )

    def format(self, record):
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for field in self.structured_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value

        if record.exc_info:
            payload["exception_type"] = record.exc_info[0].__name__

        return json.dumps(payload, default=str, separators=(",", ":"))
