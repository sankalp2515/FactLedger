"""Set isolated API storage before any application module is imported."""

import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix="-workspace-tests.db")
os.environ["ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="workspace-artifact-tests-")
os.environ["MODE"] = "development"
