"""Check the Git publication set without printing file contents or credentials."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = {".git", ".data", ".execution", ".venv", "node_modules", "__pycache__"}
SECRET = re.compile(
    rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
    rb"gsk_[A-Za-z0-9]{40,}|sk-[A-Za-z0-9_-]{40,}|"
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
    rb"(?:SERPAPI_API_KEY|GROQ_API_KEY|NVIDIA_API_KEY|OIDC_CLIENT_SECRET)"
    rb"[\"']?\s*[:=]\s*[\"']?[A-Za-z0-9_-]{24,})"
)
LINK = re.compile(r"!?\[[^\]]*\]\(([^\s)]+)(?:\s+[^)]*)?\)")


def publication_files():
    output = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    )
    return sorted({Path(name.decode()) for name in output.split(b"\0") if name})


def history_secrets():
    objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=ROOT)
    names = {}
    for line in objects.decode("utf-8").splitlines():
        oid, _, name = line.partition(" ")
        names[oid] = name
    payload = "".join(f"{oid}\n" for oid in names).encode()
    result = subprocess.run(
        ["git", "cat-file", "--batch"], cwd=ROOT, input=payload, stdout=subprocess.PIPE, check=True
    ).stdout
    failures = []
    offset = 0
    blobs = 0
    while offset < len(result):
        end = result.index(b"\n", offset)
        oid, kind, size = result[offset:end].decode().split()
        offset = end + 1
        content = result[offset : offset + int(size)]
        offset += int(size) + 1
        if kind == "blob":
            blobs += 1
            if SECRET.search(content):
                failures.append(
                    f"Possible credential in Git history: {names[oid]} ({oid[:12]}; value withheld)"
                )
    print(f"Git history check: {blobs} file versions")
    return failures


def main():
    failures = history_secrets()
    checked = 0
    for relative in publication_files():
        path = ROOT / relative
        if not path.is_file():
            continue
        if FORBIDDEN.intersection(relative.parts) or (
            relative.name.startswith(".env") and relative.name != ".env.example"
        ):
            failures.append(f"Private/generated path in publication set: {relative.as_posix()}")
            continue
        data = path.read_bytes()
        checked += 1
        if SECRET.search(data):
            failures.append(f"Possible credential in: {relative.as_posix()} (value withheld)")
        if path.suffix.lower() != ".md":
            continue
        for target in LINK.findall(data.decode("utf-8")):
            parsed = urlsplit(target.strip("<>"))
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            local = (path.parent / unquote(parsed.path)).resolve()
            if not local.is_relative_to(ROOT) or not local.exists():
                failures.append(f"Broken local Markdown link in: {relative.as_posix()}")
    for failure in sorted(set(failures)):
        print(failure)
    print(f"Publication check: {checked} files; {len(set(failures))} issues")
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())
