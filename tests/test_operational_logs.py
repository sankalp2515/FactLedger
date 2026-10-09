import json
import logging

from product_core.observability import JsonFormatter


def test_operational_record_uses_only_allowlisted_fields():
    record = logging.LogRecord("factledger", logging.INFO, "", 1, "request.completed", (), None)
    record.request_id = "id"
    record.route = "/v1/cases/{case_id}"
    record.duration_ms = 3.5
    record.api_key = "do-not-log"
    record.authorization = "secret"
    record.query = "private words"
    encoded = JsonFormatter().format(record)
    data = json.loads(encoded)
    assert data["event"] == "request.completed"
    assert data["request_id"] == "id"
    assert all(value not in encoded for value in ("do-not-log", "secret", "private words"))
