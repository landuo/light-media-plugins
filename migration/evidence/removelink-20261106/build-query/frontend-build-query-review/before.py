#!/usr/bin/env python3
"""Build complete, verified Linux/amd64 plugin ZIPs; never upload or overwrite.

The output is the existing host's go-plugins.v1.json format. A frontend plugin
must declare an actual build command and isolated output in build-plugins.json.
Static asset-reference checks are a packaging guard, not browser/Vue acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unicodedata
from urllib.parse import quote, urlsplit
import zipfile

MAX_INDEX = 2 << 20
MAX_ARCHIVE = 64 << 20
MAX_EXPANDED = 128 << 20
MAX_FILES = 4096
CONTRACTS = {"light-media.sdk-pure/v1", "light-media.sdk-base/v1", "light-media.sdk-resources/v1"}
FRONTEND_EXTENSIONS = {".js", ".mjs", ".css", ".json", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".otf"}

class BuildError(Exception):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or value in {".", ".."} or len(value.encode("utf-8")) > 1024 or "\\" in value or any(unicodedata.category(c) in {"Cc", "Cf", "Zl", "Zp"} for c in value):
        raise BuildError("invalid package-relative path")
    p = PurePosixPath(value)
    if p.is_absolute() or str(p) != value or len(p.parts) > 16 or any(s in {".", ".."} or s.endswith(".") for s in p.parts):
        raise BuildError("noncanonical package-relative path")
    if any(s.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]} for s in p.parts):
        raise BuildError("reserved package path")
    if any(not (part[0].isalnum() or part[0] == "_") or len(part.encode("utf-8")) > 255 for part in p.parts) or len(value) >= 2 and value[1] == ":":
        raise BuildError("unsupported package path component")
    if p.parts[0] == ".acquired.json":
        raise BuildError("host receipt must not be packaged")
    return p


def owned_source(root: Path, relative: str, directory: bool = False) -> Path:
    parts = relative_path(relative).parts
    current = root
    for part in parts:
        current /= part
        if current.is_symlink():
            raise BuildError(f"symlink input rejected: {relative}")
    if directory:
        if not current.is_dir():
            raise BuildError(f"missing input directory: {relative}")
    elif not current.is_file():
        raise BuildError(f"missing regular input file: {relative}")
    return current


def release_base(value: str) -> str:
    p = urlsplit(value)
    if p.scheme != "https" or not p.netloc or not p.hostname or p.username is not None or p.password is not None or p.query or p.fragment or "\\" in value or any(ord(c) <= 32 for c in value):
        raise BuildError("release base URL must be explicit HTTPS without credentials, query or fragment")
    try:
        _ = p.port
    except ValueError as exc:
        raise BuildError("invalid release URL port") from exc
    return value.rstrip("/") + "/"


def read_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BuildError("cannot read build configuration") from exc
    if not isinstance(config, dict) or set(config) != {"plugins"} or not isinstance(config["plugins"], list) or not config["plugins"]:
        raise BuildError("build configuration must contain a nonempty plugins list")
    seen = set()
    for plugin in config["plugins"]:
        if not isinstance(plugin, dict) or set(plugin) - {"id", "package", "host_contract", "license_files", "frontend"}:
            raise BuildError("unknown build plugin field")
        identity = plugin.get("id", "")
        if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,127}", identity) or identity.lower() in seen:
            raise BuildError("invalid or duplicate plugin ID")
        seen.add(identity.lower())
        package = plugin.get("package", "")
        if not isinstance(package, str) or not package.startswith("./"):
            raise BuildError("Go package must be explicit and repository-relative")
        relative_path(package[2:])
        if plugin.get("host_contract") not in CONTRACTS:
            raise BuildError("unsupported host contract")
        licenses = plugin.get("license_files")
        if not isinstance(licenses, list) or not licenses or not all(isinstance(x, str) for x in licenses):
            raise BuildError("each plugin requires an explicit license file allowlist")
        if len(licenses) != len(set(licenses)):
            raise BuildError("duplicate license files")
        for name in licenses:
            relative_path(name)
    return config


def add_file(files: dict[str, bytes], name: str, content: bytes) -> None:
    relative_path(name)
    if name in files or name.casefold() in {n.casefold() for n in files}:
        raise BuildError(f"duplicate or case-colliding package member: {name}")
    for existing in files:
        if name.startswith(existing + "/") or existing.startswith(name + "/"):
            raise BuildError("package file shadows directory")
        old, new = existing.split("/"), name.split("/")
        for i in range(min(len(old), len(new))):
            if old[i].casefold() == new[i].casefold() and old[i] != new[i] and old[:i] == new[:i]:
                raise BuildError("case-colliding package directory")
            if old[i] != new[i]:
                break
    if len(files) >= MAX_FILES or sum(map(len, files.values())) + len(content) > MAX_EXPANDED:
        raise BuildError("package exceeds host expanded size/file-count bound")
    files[name] = content


def frontend_contract(manifest: dict) -> dict | None:
    front = manifest.get("frontend")
    if front is None:
        return None
    expected = {"contract", "root", "entry", "exposes", "shared", "api_contract"}
    if not isinstance(front, dict) or set(front) != expected:
        raise BuildError("invalid frontend manifest fields")
    if front["contract"] != "light-media.vue-federation/v1" or front["api_contract"] != "light-media.plugin-api/v1":
        raise BuildError("unsupported frontend ABI")
    root, entry = relative_path(front["root"]), relative_path(front["entry"])
    if entry.name != "remoteEntry.js" or manifest["entry"] == str(root) or manifest["entry"].startswith(str(root) + "/"):
        raise BuildError("frontend entry/root conflicts with worker")
    exposed, shared = front["exposes"], front["shared"]
    if not isinstance(exposed, list) or not 1 <= len(exposed) <= 64 or not all(isinstance(x, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", x) for x in exposed) or len(set(exposed)) != len(exposed):
        raise BuildError("invalid frontend exposed components")
    if not isinstance(shared, list) or not all(isinstance(x, str) for x in shared) or "vue" not in shared or not set(shared) <= {"vue", "vuetify"} or len(shared) != len(set(shared)):
        raise BuildError("invalid frontend shared modules")
    return front


def static_asset_references(name: str, content: bytes) -> list[str]:
    suffix = PurePosixPath(name).suffix.lower()
    if suffix not in {".js", ".mjs", ".css"}:
        return []
    try:
        source = content.decode("utf-8")
    except UnicodeError as exc:
        raise BuildError("frontend code is not UTF-8") from exc
    if suffix == ".css":
        patterns = [r'''url\(\s*["']?([^\s)'";]+)''', r'''@import\s*["']([^"']+)["']''']
    else:
        patterns = [r'''\b(?:import|export)\s+(?:[^;'"\n]{0,200}?\s+from\s*)?["']([^"']+)["']''', r'''\bimport\s*\(\s*["']([^"']+)["']''', r'''\bnew\s+URL\s*\(\s*["']([^"']+)["']''']
    return [ref for pattern in patterns for ref in re.findall(pattern, source)]


def collect_frontend(output: Path, front: dict) -> dict[str, bytes]:
    if not output.is_dir() or output.is_symlink():
        raise BuildError("frontend build did not produce its declared output directory")
    files: dict[str, bytes] = {}
    for directory, directories, names in os.walk(output, followlinks=False):
        for name in directories + names:
            p = Path(directory) / name
            if p.is_symlink():
                raise BuildError("frontend symlink/escape rejected")
            if not p.is_dir() and not stat.S_ISREG(p.stat().st_mode):
                raise BuildError("frontend special file rejected")
        for name in sorted(names):
            p = Path(directory) / name
            relative = p.relative_to(output).as_posix()
            if p.suffix.lower() not in FRONTEND_EXTENSIONS:
                raise BuildError(f"unsupported frontend asset type: {relative}")
            if p.stat().st_size > MAX_EXPANDED - sum(map(len, files.values())):
                raise BuildError("frontend exceeds host expanded size bound")
            add_file(files, relative, p.read_bytes())
    if not files.get(front["entry"]):
        raise BuildError("frontend package lacks its nonempty manifest entry")
    for name, content in files.items():
        for reference in static_asset_references(name, content):
            if reference.startswith(("data:", "#")):
                continue
            if reference in front["shared"]:
                continue
            parsed = urlsplit(reference)
            if parsed.scheme or parsed.netloc or parsed.query or parsed.fragment or reference.startswith("/") or "\\" in reference:
                raise BuildError("frontend graph must use package-relative asset URLs")
            if not reference.startswith(".") and PurePosixPath(name).suffix.lower() != ".css":
                raise BuildError(f"unresolved non-shared frontend module: {reference}")
            parts = list(PurePosixPath(name).parent.parts)
            for part in reference.split("/"):
                if part in {"", "."}:
                    continue
                if part == "..":
                    if not parts:
                        raise BuildError("frontend asset reference escapes output root")
                    parts.pop()
                else:
                    parts.append(part)
            target = "/".join(parts)
            if target not in files:
                raise BuildError(f"frontend graph references missing asset: {target}")
    return files


def command(argv: list[str], cwd: Path, env: dict[str, str], timeout: int = 600) -> bytes:
    try:
        completed = subprocess.run(argv, cwd=cwd, env=env, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        # Do not blindly publish build-tool environment or stderr into CI logs.
        raise BuildError(f"command failed: {Path(argv[0]).name}") from exc
    return completed.stdout


def build_frontend(root: Path, build: Path, spec: dict, front: dict, env: dict[str, str]) -> dict[str, bytes]:
    options = spec.get("frontend")
    if not isinstance(options, dict) or set(options) != {"command", "cwd", "output"}:
        raise BuildError("frontend manifest requires an explicit build command, cwd and isolated output")
    argv = options["command"]
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv) or not any("{output}" in x or "{build_dir}" in x for x in argv):
        raise BuildError("frontend command must be an argument array using {output} or {build_dir}")
    output = build.joinpath(*relative_path(options["output"]).parts)
    if output.exists() or output.is_symlink():
        raise BuildError("frontend output already exists")
    cwd = root if options["cwd"] == "." else owned_source(root, options["cwd"], directory=True)
    try:
        argv = [x.format(output=str(output), build_dir=str(build)) for x in argv]
    except (KeyError, ValueError) as exc:
        raise BuildError("unknown frontend command placeholder") from exc
    command(argv, cwd, {**env, "LIGHT_MEDIA_FRONTEND_OUTPUT": str(output)})
    return collect_frontend(output, front)


def validate_manifest(raw: bytes, identity: str) -> dict:
    if not raw or len(raw) > MAX_INDEX:
        raise BuildError("manifest is empty or oversized")
    try:
        manifest = json.loads(raw)
    except ValueError as exc:
        raise BuildError("worker --manifest did not return one JSON object") from exc
    if not isinstance(manifest, dict) or manifest.get("plugin_id") != identity or manifest.get("schema_version") != 1 or manifest.get("runtime") != "go-executable":
        raise BuildError("worker manifest identity/runtime mismatch")
    if not isinstance(manifest.get("version"), str) or not re.fullmatch(r"[0-9]+(?:\.[0-9]+){0,3}(?:[-+][A-Za-z0-9.-]+)?", manifest["version"]):
        raise BuildError("worker manifest has invalid version")
    relative_path(manifest.get("entry"))
    frontend_contract(manifest)
    return manifest


def archive_plugin(path: Path, files: dict[str, bytes]) -> None:
    if not files or len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_EXPANDED:
        raise BuildError("invalid complete package file inventory")
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(files):
            relative_path(name)
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o600) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, files[name])
    if path.stat().st_size > MAX_ARCHIVE:
        raise BuildError("archive exceeds host compressed size bound")


def license_inventory(root: Path, specs: list[dict], local_probe: bool = False) -> dict[str, bytes]:
    names = set()
    for spec in specs:
        names.update(spec["license_files"])
    if not local_probe:
        names.add("LICENSE")
    files: dict[str, bytes] = {}
    for name in sorted(names):
        add_file(files, name, owned_source(root, name).read_bytes())
    return files


def build_plugin(root: Path, build: Path, spec: dict, base: str, go: str, local_probe: bool = False) -> tuple[dict, Path]:
    licenses = license_inventory(root, [spec], local_probe)
    env = {**os.environ, "GOOS": "linux", "GOARCH": "amd64", "CGO_ENABLED": "0"}
    worker = build / "compiled-worker"
    owned_source(root, spec["package"][2:], directory=True)
    command([go, "build", "-trimpath", "-buildvcs=false", "-o", str(worker), spec["package"]], root, env)
    manifest = validate_manifest(command([str(worker), "--manifest"], root, env, timeout=30), spec["id"])
    files: dict[str, bytes] = {}
    binary = worker.read_bytes()
    add_file(files, manifest["entry"], binary)
    for name, content in licenses.items():
        add_file(files, name, content)
    front = frontend_contract(manifest)
    if front is not None:
        for name, data in build_frontend(root, build, spec, front, env).items():
            add_file(files, front["root"] + "/" + name, data)
    elif spec.get("frontend") is not None:
        raise BuildError("build declares frontend assets but actual worker manifest does not")
    filename = f'{manifest["plugin_id"]}-{manifest["version"]}-linux-amd64.zip'
    archive = build / filename
    archive_plugin(archive, files)
    data = archive.read_bytes()
    artifact = {"platform": "linux-amd64", "url": base + quote(filename, safe=""), "sha256": digest(data), "size": len(data), "format": "zip", "executable_sha256": digest(binary), "host_contract": spec["host_contract"], "files": [{"path": name, "size": len(files[name]), "sha256": digest(files[name])} for name in sorted(files)]}
    index = {"schema_version": 1, "plugin_id": manifest["plugin_id"], "current_version": manifest["version"], "releases": [{"version": manifest["version"], "manifest": manifest, "artifacts": [artifact]}]}
    return index, archive


def fresh_output(path: Path) -> Path:
    path = path.absolute()
    if ".." in path.parts:
        raise BuildError("output path must be canonical")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink():
            raise BuildError("output path contains a symlink")
    if path.exists():
        raise BuildError("output already exists; choose a fresh path (no files will be overwritten)")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def publish_fresh(output: Path, archives: list[Path], index: dict) -> None:
    payload = (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode()
    if len(payload) > MAX_INDEX:
        raise BuildError("index exceeds host bound")
    # mkdir is the exclusive ownership claim. No rename may replace an existing
    # empty directory and no file open may truncate an unknown existing file.
    output.mkdir(mode=0o700, exist_ok=False)
    for archive in archives:
        with (output / archive.name).open("xb") as target, archive.open("rb") as source:
            shutil.copyfileobj(source, target)
    with (output / "go-plugins.v1.json").open("xb") as target:
        target.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="fresh output directory; must not already exist")
    parser.add_argument("--release-base-url", required=True, help="explicit HTTPS directory containing the release ZIPs")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().parents[1] / "build-plugins.json")
    parser.add_argument("--plugin", action="append", default=[], help="optional exact plugin ID (repeatable)")
    parser.add_argument("--go", default="go", help="Go executable (default: go on PATH)")
    parser.add_argument("--local-probe", action="store_true", help="explicit non-publishable local probe: do not require pending root LICENSE")
    args = parser.parse_args(argv)
    try:
        if sys.platform != "linux" or platform.machine().lower() not in {"x86_64", "amd64"}:
            raise BuildError("build on Linux/amd64 so the actual release worker --manifest can run")
        root = Path(__file__).resolve().parents[1]
        base = release_base(args.release_base_url)
        output = fresh_output(args.output)
        config = read_config(args.config)
        selected = [p for p in config["plugins"] if not args.plugin or p["id"] in args.plugin]
        if not selected or set(args.plugin) - {p["id"] for p in selected}:
            raise BuildError("requested plugin is absent from build configuration")
        with tempfile.TemporaryDirectory(prefix=".plugin-build-", dir=output.parent) as temp:
            indexes, archives = [], []
            for i, spec in enumerate(selected):
                build = Path(temp) / str(i)
                build.mkdir()
                index, archive = build_plugin(root, build, spec, base, args.go, args.local_probe)
                indexes.append(index)
                archives.append(archive)
            notices = Path(temp) / "THIRD_PARTY_LICENSES.zip"
            archive_plugin(notices, license_inventory(root, selected, args.local_probe))
            archives.append(notices)
            publish_fresh(output, archives, {"schema_version": 1, "plugins": indexes})
        print(json.dumps({"output": str(output), "plugins": [p["plugin_id"] for p in indexes], "platform": "linux-amd64", "publishable": not args.local_probe}, ensure_ascii=False))
        return 0
    except (BuildError, OSError) as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
