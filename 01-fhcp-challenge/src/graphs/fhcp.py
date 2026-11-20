"""Load the manifest-selected FHCP data without mixing graphs and tours."""

import hashlib
from io import BytesIO
import json
from pathlib import Path
import re

from .graph import Graph, GraphError
from .readers import read_hcp, read_tour


_CHECKOUT = Path(__file__).resolve().parents[2]
_MANIFEST = Path("docs/decisions/fhcp-instances.json")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def _selection(root: Path, instance_id: str, manifest_path: str | Path | None = None) -> tuple[dict, str]:
    """Find an unambiguous ID in the versioned selection."""
    try:
        manifest_bytes = (root / (manifest_path or _MANIFEST)).read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GraphError("manifest_mismatch", "Expected a UTF-8 JSON manifest.") from error
    if (
        not isinstance(manifest, dict)
        or type(manifest.get("manifest_version")) is not int
        or manifest["manifest_version"] != 1
        or not isinstance(manifest.get("instances"), list)
        or any(not isinstance(entry, dict) for entry in manifest["instances"])
    ):
        raise GraphError("manifest_mismatch", "Expected FHCP manifest version 1 with instances.")
    matches = [entry for entry in manifest["instances"] if entry.get("id") == instance_id]
    if len(matches) != 1:
        raise GraphError("manifest_mismatch", f"Expected one selection entry for {instance_id!r}.")
    return matches[0], hashlib.sha256(manifest_bytes).hexdigest()


def _verified_member(directory: Path, record: dict, suffix: str) -> tuple[bytes, str]:
    member, expected = record.get("archive_member"), record.get("sha256")
    if not isinstance(member, str) or not re.fullmatch(r"[A-Za-z0-9_-]+" + re.escape(suffix), member):
        raise GraphError("manifest_mismatch", f"Expected a local {suffix} member name.")
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected):
        raise GraphError("manifest_mismatch", f"Invalid SHA-256 in manifest for {member}.")
    directory = directory.resolve()
    path = (directory / member).resolve()
    if path.parent != directory:
        raise GraphError("manifest_mismatch", f"Member {member} resolves outside its directory.")
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected:
        raise GraphError(
            "source_hash_mismatch",
            f"{member}: expected SHA-256 {expected}, got {actual}.",
        )
    return payload, actual


def _check_counts(graph: Graph, entry: dict) -> None:
    for field, actual in (("dimension", graph.vertex_count()), ("edge_count", graph.edge_count())):
        expected = entry.get(field)
        if type(expected) is not int or expected != actual:
            raise GraphError("manifest_mismatch", f"{entry['id']}: expected {field} {expected!r}, got {actual}.")


def load_fhcp_graph(
    instance_id: str, *, root: str | Path = _CHECKOUT, manifest: str | Path | None = None,
) -> Graph:
    """Read a selected HCP by ID, checking the same bytes supplied to the parser."""
    root = Path(root)
    entry, revision = _selection(root, instance_id, manifest)
    payload, sha256 = _verified_member(root / "data/raw/FHCPCS", entry, ".hcp")
    graph = read_hcp(BytesIO(payload), source={
        "instance_id": instance_id,
        "sha256": sha256,
        "source_path": (Path("data/raw/FHCPCS") / entry["archive_member"]).as_posix(),
        "manifest_revision": revision,
    })
    _check_counts(graph, entry)
    return graph


def load_fhcp_certificate(graph: Graph, *, root: str | Path = _CHECKOUT) -> tuple[int, ...]:
    """Read the selected tour for a graph's provenance, returning external labels."""
    instance_id = graph.source.get("instance_id")
    graph_hash = graph.source.get("sha256", "")
    if not instance_id or not _SHA256.fullmatch(graph_hash):
        raise GraphError("manifest_mismatch", "Expected a graph with FHCP instance provenance.")
    root = Path(root)
    entry, _ = _selection(root, instance_id)
    if graph_hash != entry.get("sha256"):
        raise GraphError("manifest_mismatch", f"{instance_id}: graph SHA-256 differs from manifest.")
    _check_counts(graph, entry)
    certificate = entry.get("certificate")
    if not isinstance(certificate, dict):
        raise GraphError("manifest_mismatch", f"{instance_id}: missing certificate entry.")
    payload, _ = _verified_member(root / "data/raw/FHCPCS_sols", certificate, ".hcp.tou")
    return read_tour(BytesIO(payload), graph)
