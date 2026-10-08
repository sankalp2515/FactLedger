import importlib.util
import os
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from product_core.models import Membership
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

spec = importlib.util.spec_from_file_location(
    "bootstrap", Path(__file__).parents[2] / "scripts/bootstrap_oidc.py"
)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)


def test_oidc_identity_matches_login_without_normalizing_issuer():
    assert (
        bootstrap.identity_id("https://id.example/", "subject")
        == sha256(b"https://id.example/|subject").hexdigest()
    )
    assert bootstrap.identity_id("https://id.example/", "subject") != bootstrap.identity_id(
        "https://id.example", "subject"
    )
    for issuer in ["http://id.example", "https://user:secret@id.example", "https://id.example?secret=x"]:
        with pytest.raises(ValueError):
            bootstrap.identity_id(issuer, "subject")


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL", "").startswith("postgresql"), reason="PostgreSQL integration only"
)
def test_bootstrap_is_idempotent_and_refuses_role_overwrite(monkeypatch):
    engine = create_engine(os.environ["DATABASE_URL"])
    workspace_id = str(uuid4())
    subject = str(uuid4())
    with engine.connect() as connection:
        transaction = connection.begin()
        factory = sessionmaker(bind=connection, join_transaction_mode="create_savepoint")
        monkeypatch.setattr(bootstrap, "SessionLocal", factory)
        try:
            user_id = bootstrap.provision(
                "https://id.example", subject, "Synthetic", workspace_id, "Synthetic", "owner"
            )
            assert (
                bootstrap.provision(
                    "https://id.example", subject, "Synthetic", workspace_id, "Synthetic", "owner"
                )
                == user_id
            )
            with factory() as session:
                assert session.get(Membership, (workspace_id, user_id)).role == "owner"
            with pytest.raises(ValueError, match="another role"):
                bootstrap.provision(
                    "https://id.example", subject, "Synthetic", workspace_id, "Synthetic", "researcher"
                )
        finally:
            transaction.rollback()
    engine.dispose()
