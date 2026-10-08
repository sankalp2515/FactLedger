import http.client
import ipaddress
import multiprocessing
import socket
import ssl
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

MAX_BYTES = 20 * 1024 * 1024
MAX_TEXT = 2_000_000


@dataclass
class AcquiredDocument:
    title: str
    text: str
    raw: bytes
    media_type: str
    metadata: dict = field(default_factory=dict)


def validate_url(url: str, resolver=None) -> tuple[str, list[str]]:
    if len(url) > 4096:
        raise ValueError("URL_TOO_LONG")
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        raise ValueError("INVALID_URL") from None
    if (
        parts.scheme != "https"
        or not parts.hostname
        or parts.username
        or parts.password
        or port not in (None, 443)
    ):
        raise ValueError("PUBLIC_HTTPS_REQUIRED")
    hostname = parts.hostname.encode("idna").decode("ascii")
    try:
        addresses = [str(ipaddress.ip_address(hostname))]
    except ValueError:
        addresses = (
            resolver(hostname)
            if resolver
            else list({row[4][0] for row in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
        )
    if not addresses:
        raise ValueError("DNS_EMPTY")
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if (
            not ip.is_global
            or ip.is_multicast
            or (getattr(ip, "ipv4_mapped", None) and not ip.ipv4_mapped.is_global)
        ):
            raise ValueError("NON_PUBLIC_ADDRESS")
    return hostname, addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, hostname, address, timeout):
        super().__init__(hostname, 443, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
        self.in_title = False
        self.title = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag in {"p", "div", "br", "li", "tr", "h1", "h2", "h3"} and not self.hidden:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden = max(0, self.hidden - 1)
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)
            if self.in_title:
                self.title.append(data)


def _pdf_child(raw, ranges, connection):
    try:
        import io
        import os

        if os.name != "nt":
            import resource

            resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
            resource.setrlimit(resource.RLIMIT_CPU, (20, 20))

        # Parser has no network authority, even if a future library adds fetching.
        def denied(*args, **kwargs):
            raise PermissionError("PDF_NETWORK_DISABLED")

        socket.socket = denied
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise ValueError("ENCRYPTED_PDF")
        total = len(reader.pages)
        selected = []
        if ranges:
            for first, last in ranges:
                if first < 1 or last < first or last > total:
                    raise ValueError("INVALID_PAGE_RANGE")
                selected.extend(range(first - 1, last))
            selected = sorted(set(selected))
        else:
            selected = list(range(min(total, 100)))
        if len(selected) > 100:
            raise ValueError("PDF_PAGE_LIMIT")
        pages = []
        pieces = []
        offset = 0
        for index in selected:
            text = reader.pages[index].extract_text() or ""
            if offset + len(text) > MAX_TEXT:
                raise ValueError("TEXT_LIMIT")
            pages.append({"page": index + 1, "start": offset, "end": offset + len(text)})
            pieces.append(text)
            offset += len(text) + 1
        text = "\n".join(pieces)
        connection.send(
            {
                "text": text,
                "metadata": {
                    "total_pages": total,
                    "extracted_pages": len(selected),
                    "pages": pages,
                    "partial": len(selected) < total,
                    "scanned": not bool(text.strip()),
                    "extraction_version": "pypdf-v1",
                },
            }
        )
    except Exception as exc:  # noqa: BLE001 -- Untrusted PDF parser failures cross a safe IPC boundary.
        connection.send({"error": type(exc).__name__})
    finally:
        connection.close()


def extract_pdf(raw: bytes, page_ranges=None) -> tuple[str, dict]:
    if page_ranges and (
        len(page_ranges) > 100
        or any(len(r) != 2 or not all(isinstance(v, int) for v in r) for r in page_ranges)
    ):
        raise ValueError("INVALID_PAGE_RANGE")
    context = multiprocessing.get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_pdf_child, args=(raw, page_ranges, child), daemon=True)
    process.start()
    child.close()
    deadline = time.monotonic() + 20
    try:
        import psutil

        while time.monotonic() < deadline:
            if parent.poll(0.05):
                result = parent.recv()
                if "error" in result:
                    raise ValueError("PDF_EXTRACTION_FAILED:" + result["error"])
                return result["text"], result["metadata"]
            if not process.is_alive():
                raise ValueError("PDF_PARSER_EXITED")
            try:
                if psutil.Process(process.pid).memory_info().rss > 512 * 1024 * 1024:
                    raise ValueError("PDF_MEMORY_LIMIT")
            except psutil.NoSuchProcess:
                raise ValueError("PDF_PARSER_EXITED") from None
        raise ValueError("PDF_TIMEOUT")
    finally:
        if process.is_alive():
            process.terminate()
        process.join(timeout=2)
        parent.close()


def extract_document(raw: bytes, media_type: str, page_ranges=None) -> AcquiredDocument:
    if len(raw) > MAX_BYTES:
        raise ValueError("DOCUMENT_SIZE_LIMIT")
    media_type = media_type.split(";")[0].lower()
    if raw.startswith(b"%PDF-") or media_type == "application/pdf":
        text, metadata = extract_pdf(raw, page_ranges)
        return AcquiredDocument("PDF record", text, raw, "application/pdf", metadata)
    if media_type not in {"text/html", "text/plain", "application/xhtml+xml"}:
        raise ValueError("UNSUPPORTED_MEDIA_TYPE")
    decoded = raw.decode("utf-8", errors="replace")
    title = "Public record"
    if media_type != "text/plain":
        parser = _Text()
        parser.feed(decoded)
        decoded = "".join(parser.parts)
        title = "".join(parser.title).strip()[:300] or title
    partial = len(decoded) > MAX_TEXT
    return AcquiredDocument(
        title,
        decoded[:MAX_TEXT],
        raw,
        media_type,
        {
            "extraction_version": "html-text-v1",
            "partial": partial,
            "characters_total": len(decoded),
            "characters_extracted": min(len(decoded), MAX_TEXT),
        },
    )


def acquire(url: str, page_ranges: list[list[int]] | None = None) -> AcquiredDocument:
    started = time.monotonic()
    original = url
    for redirect in range(6):
        hostname, addresses = validate_url(url)
        parts = urlsplit(url)
        remaining = 20 - (time.monotonic() - started)
        if remaining <= 0:
            raise ValueError("FETCH_TIMEOUT")
        connection = _PinnedHTTPS(hostname, addresses[0], remaining)
        try:
            connection.request(
                "GET",
                (parts.path or "/") + ("?" + parts.query if parts.query else ""),
                headers={
                    "Host": hostname,
                    "User-Agent": "PublicEvidenceResearch/1.0",
                    "Accept": "text/html,application/pdf,text/plain",
                    "Accept-Encoding": "identity",
                },
            )
            response = connection.getresponse()
            if response.status in {301, 302, 303, 307, 308}:
                location = response.getheader("Location")
                if not location:
                    raise ValueError("REDIRECT_WITHOUT_LOCATION")
                url = urljoin(url, location)
                continue
            if response.status != 200:
                raise ValueError("SOURCE_HTTP_" + str(response.status))
            if response.getheader("Content-Encoding", "identity") != "identity":
                raise ValueError("COMPRESSED_RESPONSE_REJECTED")
            length = response.getheader("Content-Length")
            if length and int(length) > MAX_BYTES:
                raise ValueError("DOCUMENT_SIZE_LIMIT")
            data = bytearray()
            while True:
                remaining = 20 - (time.monotonic() - started)
                if remaining <= 0:
                    raise ValueError("FETCH_TIMEOUT")
                if connection.sock:
                    connection.sock.settimeout(remaining)
                block = response.read(min(65536, MAX_BYTES + 1 - len(data)))
                if not block:
                    break
                data.extend(block)
                if len(data) > MAX_BYTES:
                    raise ValueError("DOCUMENT_SIZE_LIMIT")
            doc = extract_document(bytes(data), response.getheader("Content-Type", ""), page_ranges)
            doc.metadata.update(
                url=original,
                final_url=url,
                source_type="pdf" if doc.media_type == "application/pdf" else "web",
                retrieved_at=__import__("datetime")
                .datetime.now(__import__("datetime").timezone.utc)
                .isoformat(),
                publication_date=None,
                event_date=None,
                date_provenance="unknown",
            )
            return doc
        finally:
            connection.close()
    raise ValueError("REDIRECT_LIMIT")
