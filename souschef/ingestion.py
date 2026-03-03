"""Chef Server ingestion and offline bundle utilities."""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from souschef.core.chef_server import ChefServerClient, build_chef_server_client
from souschef.core.path_utils import (
    _ensure_within_base_path,
    _get_workspace_root,
    _normalize_path,
)
from souschef.filesystem.operations import create_tar_gz_archive, extract_tar_gz_archive


@dataclass(frozen=True)
class CookbookSpec:
    """Cookbook name and version pairing."""

    name: str
    version: str


@dataclass
class CookbookFetchResult:
    """Cookbook fetch results with dependency details."""

    root_dir: Path
    cookbooks: list[CookbookSpec]
    dependency_graph: dict[str, dict[str, str]]
    manifest_path: Path
    offline_bundle_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


def fetch_cookbooks_from_chef_server(
    *,
    cookbook: CookbookSpec,
    additional_cookbooks: list[CookbookSpec] | None,
    server_url: str,
    organisation: str,
    client_name: str,
    client_key_path: str | None,
    client_key: str | None,
    output_dir: str | None = None,
    dependency_depth: str = "full",
    use_cache: bool = True,
    cache_dir: str | None = None,
    offline_bundle_path: str | None = None,
) -> CookbookFetchResult:
    """
    Fetch cookbooks and dependency closure from Chef Server.

    Args:
        cookbook: Primary cookbook specification.
        additional_cookbooks: Extra cookbooks to include from run_list or policy.
        server_url: Chef Server URL.
        organisation: Chef organisation name.
        client_name: Chef client name.
        client_key_path: Client key path.
        client_key: Inline client key content.
        output_dir: Optional output directory for fetched cookbooks.
        dependency_depth: Dependency depth (direct, transitive, full).
        use_cache: Reuse cached cookbook downloads when possible.
        cache_dir: Override cache directory.
        offline_bundle_path: Optional tar.gz path for offline bundle export.

    Returns:
        CookbookFetchResult with downloaded paths and metadata.

    """
    client = build_chef_server_client(
        server_url=server_url,
        organisation=organisation,
        client_name=client_name,
        client_key_path=client_key_path,
        client_key=client_key,
    )

    if output_dir:
        workspace_root = _get_workspace_root()
        output_root = _ensure_within_base_path(
            _normalize_path(output_dir), workspace_root
        )
    else:
        output_root = Path(tempfile.mkdtemp(prefix="souschef-cookbooks-"))

    cache_root = _resolve_cache_root(cache_dir)

    requested = [cookbook]
    if additional_cookbooks:
        requested.extend(additional_cookbooks)

    closure, dependency_graph, warnings = _resolve_dependency_closure(
        client=client,
        requested=requested,
        dependency_depth=dependency_depth,
    )

    cookbook_root = output_root / "cookbooks"
    cookbook_root.mkdir(parents=True, exist_ok=True)

    for spec in closure:
        _download_cookbook(
            client=client,
            spec=spec,
            destination=cookbook_root,
            use_cache=use_cache,
            cache_root=cache_root,
            warnings=warnings,
        )

    manifest_path = _write_manifest(
        root_dir=output_root,
        cookbooks=closure,
        dependency_graph=dependency_graph,
        server_url=server_url,
        organisation=organisation,
        warnings=warnings,
    )

    bundle_path: Path | None = None
    if offline_bundle_path:
        workspace_root = _get_workspace_root()
        bundle_output = _ensure_within_base_path(
            _normalize_path(offline_bundle_path), workspace_root
        )
        bundle_path = Path(create_tar_gz_archive(str(output_root), str(bundle_output)))

    return CookbookFetchResult(
        root_dir=output_root,
        cookbooks=closure,
        dependency_graph=dependency_graph,
        manifest_path=manifest_path,
        offline_bundle_path=bundle_path,
        warnings=warnings,
    )


def import_offline_bundle(bundle_path: str, output_dir: str) -> Path:
    """
    Extract an offline bundle to a local directory.

    Args:
        bundle_path: Path to the tar.gz bundle.
        output_dir: Destination directory for extracted content.

    Returns:
        Path to extracted bundle root.

    """
    workspace_root = _get_workspace_root()
    target_dir = _ensure_within_base_path(_normalize_path(output_dir), workspace_root)
    return Path(extract_tar_gz_archive(bundle_path, str(target_dir)))


def _resolve_cache_root(cache_dir: str | None) -> Path:
    """Resolve cookbook cache directory."""
    if cache_dir:
        cache_root = Path(cache_dir)
    else:
        cache_root = Path(tempfile.gettempdir()) / ".souschef" / "cookbook-cache"
    cache_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    return cache_root


def _resolve_dependency_closure(
    *,
    client: ChefServerClient,
    requested: list[CookbookSpec],
    dependency_depth: str,
) -> tuple[list[CookbookSpec], dict[str, dict[str, str]], list[str]]:
    """Resolve cookbook dependency closure from Chef metadata."""
    valid_depths = {"direct", "transitive", "full"}
    if dependency_depth not in valid_depths:
        raise ValueError("Dependency depth must be direct, transitive, or full")

    queue: list[CookbookSpec] = list(requested)
    seen: dict[str, CookbookSpec] = {}
    dependency_graph: dict[str, dict[str, str]] = {}
    warnings: list[str] = []

    while queue:
        current = _normalise_spec(client=client, spec=queue.pop(0), warnings=warnings)
        if current.name in seen:
            continue
        seen[current.name] = current

        metadata = client.get_cookbook_version(current.name, current.version)
        deps = _extract_dependencies(metadata)
        dependency_graph[current.name] = deps

        if dependency_depth == "direct":
            continue

        for dep_name, constraint in deps.items():
            version = _select_dependency_version(
                client=client,
                cookbook_name=dep_name,
                constraint=constraint,
                warnings=warnings,
            )
            if version:
                queue.append(CookbookSpec(name=dep_name, version=version))

    return list(seen.values()), dependency_graph, warnings


def _extract_dependencies(metadata: dict[str, Any]) -> dict[str, str]:
    """Extract cookbook dependency mapping from metadata payload."""
    meta = metadata.get("metadata") if isinstance(metadata, dict) else None
    if isinstance(meta, dict):
        deps = meta.get("dependencies")
        if isinstance(deps, dict):
            return {name: str(version) for name, version in deps.items()}
    deps = metadata.get("dependencies") if isinstance(metadata, dict) else None
    if isinstance(deps, dict):
        return {name: str(version) for name, version in deps.items()}
    return {}


def _select_dependency_version(
    *,
    client: ChefServerClient,
    cookbook_name: str,
    constraint: str | None,
    warnings: list[str],
) -> str | None:
    """Select cookbook version for dependency constraint."""
    available = client.list_cookbook_versions(cookbook_name)
    if not available:
        warnings.append(f"Dependency {cookbook_name} has no available versions")
        return None

    constraint_value = (constraint or "").strip()
    if not constraint_value or constraint_value in {">= 0.0.0", ">=0.0.0"}:
        return _latest_version(available)

    if constraint_value.startswith("~>"):
        base = constraint_value[2:].strip()
        matches = [v for v in available if v.startswith(base)]
        if matches:
            return _latest_version(matches)
        warnings.append(
            f"Dependency {cookbook_name} uses unsupported constraint {constraint_value}"
        )
        return _latest_version(available)

    if constraint_value.startswith(("==", "=")):
        target = constraint_value.lstrip("=").strip()
        if target in available:
            return target
        warnings.append(
            f"Dependency {cookbook_name} requested {target} but it is unavailable"
        )
        return _latest_version(available)

    if constraint_value[0].isdigit() and constraint_value in available:
        return constraint_value

    warnings.append(
        f"Dependency {cookbook_name} uses constraint {constraint_value}; using latest"
    )
    return _latest_version(available)


def _latest_version(versions: list[str]) -> str:
    """Return the latest version based on numeric sorting."""
    return sorted(versions, key=_version_key, reverse=True)[0]


def _version_key(version: str) -> tuple[int, ...]:
    """Build a numeric sort key for cookbook versions."""
    parts = []
    for token in version.replace("-", ".").split("."):
        if token.isdigit():
            parts.append(int(token))
        else:
            digits = "".join(char for char in token if char.isdigit())
            if digits:
                parts.append(int(digits))
    return tuple(parts)


def _download_cookbook(
    *,
    client: ChefServerClient,
    spec: CookbookSpec,
    destination: Path,
    use_cache: bool,
    cache_root: Path,
    warnings: list[str],
) -> None:
    """Download a cookbook version into destination directory."""
    resolved_spec = _normalise_spec(client=client, spec=spec, warnings=warnings)
    cache_dir = cache_root / resolved_spec.name / resolved_spec.version
    cookbook_dir = destination / spec.name

    if use_cache and cache_dir.exists():
        if cookbook_dir.exists():
            shutil.rmtree(cookbook_dir)
        shutil.copytree(cache_dir, cookbook_dir)
        return

    cookbook_dir.mkdir(parents=True, exist_ok=True)

    metadata = client.get_cookbook_version(resolved_spec.name, resolved_spec.version)
    items = _collect_cookbook_items(metadata)

    for item in items:
        path = item.get("path")
        url = item.get("url")
        if not path or not url:
            continue
        target_path = cookbook_dir / path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = client.download_url(url)
        except Exception as exc:
            warnings.append(
                "Failed to download "
                f"{resolved_spec.name} {resolved_spec.version} {path}: {exc}"
            )
            continue
        target_path.write_bytes(content)

    _write_cookbook_metadata(cookbook_dir, metadata)

    if use_cache:
        cache_dir.parent.mkdir(parents=True, exist_ok=True)
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
        shutil.copytree(cookbook_dir, cache_dir)


def _normalise_spec(
    *,
    client: ChefServerClient,
    spec: CookbookSpec,
    warnings: list[str],
) -> CookbookSpec:
    """Ensure a cookbook spec has a concrete version."""
    if spec.version:
        return spec
    available = client.list_cookbook_versions(spec.name)
    if not available:
        warnings.append(f"Cookbook {spec.name} has no available versions")
        return spec
    return CookbookSpec(name=spec.name, version=_latest_version(available))


def _collect_cookbook_items(metadata: dict[str, Any]) -> list[dict[str, str]]:
    """Collect cookbook file entries with paths and URLs."""
    items: list[dict[str, str]] = []
    sections = (
        "all_files",
        "files",
        "recipes",
        "templates",
        "root_files",
        "libraries",
        "resources",
        "providers",
        "definitions",
        "attributes",
    )
    for section in sections:
        items.extend(_collect_section_items(metadata, section))
    return items


def _collect_section_items(
    metadata: dict[str, Any], section: str
) -> list[dict[str, str]]:
    """Collect cookbook items for a single metadata section."""
    if not isinstance(metadata, dict):
        return []

    entries = metadata.get(section, [])
    if not isinstance(entries, list):
        return []

    items: list[dict[str, str]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        url = entry.get("url")
        if path and url:
            items.append({"path": str(path), "url": str(url)})
    return items


def _write_cookbook_metadata(cookbook_dir: Path, metadata: dict[str, Any]) -> None:
    """Write cookbook metadata to a JSON file."""
    metadata_path = cookbook_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def _write_manifest(
    *,
    root_dir: Path,
    cookbooks: list[CookbookSpec],
    dependency_graph: dict[str, dict[str, str]],
    server_url: str,
    organisation: str,
    warnings: list[str],
) -> Path:
    """Write manifest describing the downloaded cookbooks."""
    manifest = {
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "server_url": server_url,
        "organisation": organisation,
        "cookbooks": [spec.__dict__ for spec in cookbooks],
        "dependency_graph": dependency_graph,
        "warnings": warnings,
    }
    manifest_path = root_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path
