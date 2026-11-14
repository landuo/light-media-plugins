#!/usr/bin/env python3
"""Generate the source-only catalog for the checked-out Git commit."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import sys
import tempfile

from build_plugins import (
    MAX_INDEX,
    BuildError,
    add_file,
    collect_frontend,
    command,
    frontend_contract,
    license_inventory,
    owned_source,
    read_config,
    validate_manifest,
)

INDEX = "go-plugins.v2.json"


def source_entry(root: Path, spec: dict, manifest: dict, commit: str) -> dict:
    source = {
        "commit": commit,
        "package": spec["package"],
        "host_contract": spec["host_contract"],
    }
    licenses = license_inventory(root, [spec])
    if not licenses["LICENSE"].strip():
        raise BuildError("root LICENSE is empty")
    source["license_files"] = list(licenses)
    files: dict[str, bytes] = {}
    add_file(files, manifest["entry"], b"")
    for name, content in licenses.items():
        add_file(files, name, content)

    front = frontend_contract(manifest)
    options = spec.get("frontend")
    if front is not None:
        # The current registry copies tracked static frontend assets. Source
        # installation only declares their directory, with no build command.
        argv = options.get("command") if isinstance(options, dict) else None
        if not isinstance(argv, list) or len(argv) != 4 or argv[:2] != ["cp", "-R"] or argv[3] != "{output}" or options.get("cwd") != ".":
            raise BuildError("source catalog requires a tracked static frontend directory")
        directory = owned_source(root, argv[2], directory=True)
        for name, data in collect_frontend(directory, front).items():
            add_file(files, front["root"] + "/" + name, data)
        source["frontend_dir"] = argv[2]
    elif options is not None:
        raise BuildError("build declares frontend assets but worker manifest does not")

    return {
        "schema_version": 2,
        "plugin_id": manifest["plugin_id"],
        "current_version": manifest["version"],
        "releases": [{"version": manifest["version"], "manifest": manifest, "source": source}],
    }


def generate(root: Path, commit: str, go: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise BuildError("expected a complete lowercase Git commit SHA")
    if command(["git", "rev-parse", "HEAD"], root, os.environ).decode().strip() != commit:
        raise BuildError("the checked-out source commit does not match the catalog pin")
    changes = command(["git", "status", "--porcelain", "--untracked-files=all", "--", ".", f":(exclude){INDEX}"], root, os.environ)
    if changes:
        raise BuildError("commit the source inputs before generating their catalog")
    arch = {"x86_64": "amd64", "aarch64": "arm64"}.get(platform.machine())
    if platform.system() != "Linux" or arch is None:
        raise BuildError("manifest generation runs on Linux amd64 or arm64")
    env = {
        **os.environ,
        "GOOS": "linux",
        "GOARCH": arch,
        "CGO_ENABLED": "0",
        "GOTOOLCHAIN": "local",
        "GOWORK": "off",
        "GOFLAGS": "-mod=readonly",
        "GOAUTH": "off",
    }
    entries = []
    with tempfile.TemporaryDirectory(prefix="light-media-plugin-catalog-") as scratch:
        worker = Path(scratch) / "worker"
        for spec in read_config(root / "build-plugins.json")["plugins"]:
            owned_source(root, spec["package"][2:], directory=True)
            command([go, "build", "-trimpath", "-buildvcs=false", "-o", str(worker), spec["package"]], root, env)
            manifest = validate_manifest(command([str(worker), "--manifest"], root, env, timeout=30), spec["id"])
            entries.append(source_entry(root, spec, manifest, commit))
    payload = (json.dumps({"schema_version": 2, "plugins": entries}, ensure_ascii=False, indent=2) + "\n").encode()
    if len(payload) > MAX_INDEX:
        raise BuildError("catalog exceeds host index size bound")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-sha", required=True, help="the full commit currently checked out")
    parser.add_argument("--go", default="go", help="Go executable (default: go on PATH)")
    args = parser.parse_args()
    try:
        root = Path(__file__).resolve().parents[1]
        target = root / INDEX
        if target.is_symlink():
            raise BuildError("catalog path is a symlink")
        target.write_bytes(generate(root, args.source_sha, args.go))
        return 0
    except (BuildError, OSError) as exc:
        print(f"source catalog failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
