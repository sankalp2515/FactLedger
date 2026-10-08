"""Conservative source dependencies; counts never determine findings."""

from collections import defaultdict


def source_families(sources: list[dict]) -> list[dict]:
    hashes = defaultdict(list)
    edges = []
    for source in sources:
        if source.get("content_hash"):
            hashes[source["content_hash"]].append(source["id"])
    for digest, ids in hashes.items():
        if len(ids) > 1:
            edges.append(
                {"kind": "EXACT_DUPLICATE", "source_ids": ids, "content_hash": digest, "confidence": "exact"}
            )
    by_url = {s.get("url"): s["id"] for s in sources if s.get("url")}
    for source in sources:
        origin = source.get("metadata", {}).get("origin_url")
        if origin in by_url and by_url[origin] != source["id"]:
            edges.append(
                {
                    "kind": "POSSIBLE_DEPENDENCE",
                    "source_ids": [source["id"], by_url[origin]],
                    "confidence": "proposed",
                    "reason": "Attributed originating URL; editorial confirmation needed.",
                }
            )
    return edges
