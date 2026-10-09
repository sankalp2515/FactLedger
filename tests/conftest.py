"""Set isolated API storage before any application module is imported."""

import os
import tempfile

os.environ["DATABASE_URL"] = "sqlite:///" + tempfile.mktemp(suffix="-workspace-tests.db")
os.environ["ARTIFACT_DIR"] = tempfile.mkdtemp(prefix="workspace-artifact-tests-")
os.environ["MODE"] = "development"
# Local .env credentials must never influence unit-test behavior or reach a provider.
for provider_key in (
    "SERPAPI_API_KEY",
    "GROQ_API_KEY",
    "NVIDIA_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
):
    os.environ[provider_key] = ""
os.environ["SESSION_SECRET"] = "unit-tests-only"
