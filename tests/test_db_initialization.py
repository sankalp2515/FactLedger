"""PostgreSQL startup must work with a read-only application filesystem."""

import os
import subprocess
import sys


def test_postgres_import_does_not_create_local_database_directories():
    environment = dict(os.environ, DATABASE_URL="postgresql+psycopg://unused@localhost/unused")
    script = "from unittest.mock import patch\nwith patch('pathlib.Path.mkdir', side_effect=AssertionError('Unexpected filesystem write')):\n import product_core.db\n assert product_core.db.engine.dialect.name == 'postgresql'\n"
    result = subprocess.run(
        [sys.executable, "-c", script], env=environment, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
