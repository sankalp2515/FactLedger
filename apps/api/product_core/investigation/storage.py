"""Private content-addressed immutable filesystem artifacts."""

import os
import re
import time
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path


@contextmanager
def _workspace_lock(root: Path, workspace_id: str):
    directory = root / ".locks"
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / (workspace_id + ".lock")).open("a+b") as lock:
        lock.seek(0, os.SEEK_END)
        if lock.tell() == 0:
            lock.write(b"1")
            lock.flush()
        deadline = time.monotonic() + 10
        while True:
            try:
                lock.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise ValueError("STORAGE_BUSY") from None
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.seek(0)
            if os.name == "nt":
                msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _write_once(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if path.read_bytes() != data:
            raise ValueError("ARTIFACT_INTEGRITY_FAILURE")


def store_document(workspace_id, case_id, document, root=None) -> dict:
    from product_core.config import Settings

    settings = Settings()
    for value in (workspace_id, case_id):
        if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", str(value)):
            raise ValueError("INVALID_ARTIFACT_SCOPE")
    if root is None:
        root = settings.artifact_dir
    root = Path(root).resolve()
    raw = document.raw
    text = document.text.encode("utf-8")
    content_hash = sha256(raw).hexdigest()
    extraction_hash = sha256(text).hexdigest()
    folder = Path(str(workspace_id)) / str(case_id) / content_hash
    artifact_path = folder / "raw"
    text_path = folder / (extraction_hash + ".txt")
    with _workspace_lock(root, str(workspace_id)):
        workspace = root / str(workspace_id)
        used = (
            sum(path.stat().st_size for path in workspace.rglob("*") if path.is_file())
            if workspace.exists()
            else 0
        )
        additional = sum(
            len(data)
            for path, data in ((root / artifact_path, raw), (root / text_path, text))
            if not path.exists()
        )
        if used + additional > settings.workspace_storage_bytes:
            raise ValueError("STORAGE_LIMIT_EXCEEDED")
        _write_once(root / artifact_path, raw)
        _write_once(root / text_path, text)
    return {
        "content_hash": content_hash,
        "extraction_hash": extraction_hash,
        "artifact_path": str(artifact_path),
        "text_path": str(text_path),
        "metadata": dict(document.metadata, media_type=document.media_type),
    }
