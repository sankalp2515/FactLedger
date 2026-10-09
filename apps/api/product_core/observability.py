"""Content-free JSON operational records; evidence and audit trails stay in PostgreSQL."""

import json
import logging
from datetime import UTC, datetime

FIELDS = (
    "request_id",
    "route",
    "method",
    "status",
    "duration_ms",
    "run_id",
    "workspace_id",
    "state",
    "error_type",
    "due_runs",
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        data.update({name: getattr(record, name) for name in FIELDS if hasattr(record, name)})
        return json.dumps(data)


logger = logging.getLogger("factledger")
logger.setLevel(logging.INFO)
logger.propagate = False
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
