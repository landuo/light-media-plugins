#!/usr/bin/env python3
"""Publish one immutable-by-convention source build; never delete or clobber.

Only the workflow's ephemeral same-repository GITHUB_TOKEN is consumed. Index
publication uses a new commit based on the observed main head and a non-force
ref update, not Contents API blob-SHA pseudo-CAS. See GitHub's official REST
releases/assets and git/refs documentation. No mutation is blindly retried.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import zipfile

INDEX = "go-plugins.v1.json"
LICENSES = "THIRD_PARTY_LICENSES.zip"
MAX_ASSET = 64 << 20
MAX_EXPANDED = 128 << 20
API_VERSION = "2026-03-10"


class PublishError(Exception):
    pass


class APIError(PublishError):
    def __init__(self, status: int | None, operation: str):
        self.status = status
        super().__init__(f"GitHub {operation} failed (status={status}); no mutation retry")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def decode_json(raw: bytes):
    def unique(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise PublishError("duplicate JSON key")
            out[key] = value
        return out
    try:
        return json.loads(raw, object_pairs_hook=unique)
    except (ValueError, UnicodeError) as exc:
        raise PublishError("invalid JSON") from exc


def regular_bytes(path: Path, limit: int = MAX_ASSET) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise PublishError(f"missing, symlink or oversized input: {path.name}")
    data = path.read_bytes()
    if len(data) > limit:
        raise PublishError("input grew beyond size limit")
    return data


def zip_members(data: bytes) -> dict[str, bytes]:
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            members = archive.infolist()
            if len(members) > 4096 or sum(x.file_size for x in members) > MAX_EXPANDED:
                raise PublishError("archive exceeds expanded size/file count limit")
            out = {}
            for item in members:
                name = item.filename
                path = PurePosixPath(name)
                mode = item.external_attr >> 16
                if not name or "\\" in name or path.is_absolute() or str(path) != name or any(p in {".", ".."} for p in path.parts) or item.is_dir() or stat.S_ISLNK(mode) or name in out:
                    raise PublishError("archive has unsafe or duplicate member")
                out[name] = archive.read(item)
            return out
    except (ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        raise PublishError("invalid release ZIP") from exc


def validate_bundle(root: Path, dist: Path, repo: str, source: str) -> dict[str, bytes]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not re.fullmatch(r"[0-9a-f]{40}", source):
        raise PublishError("expected owner/repository and complete lowercase source commit SHA")
    # The coordinator adds this actual file only after explicit license approval.
    # Neither LICENSE.upstream nor a local-probe package can substitute for it.
    license_text = regular_bytes(root / "LICENSE", 1 << 20)
    if not license_text.strip():
        raise PublishError("root LICENSE is not approved/present")
    if dist.is_symlink() or not dist.is_dir():
        raise PublishError("release output must be an owned directory")
    raw = regular_bytes(dist / INDEX, 2 << 20)
    index = decode_json(raw)
    if not isinstance(index, dict) or index.get("schema_version") != 1 or not isinstance(index.get("plugins"), list) or not index["plugins"]:
        raise PublishError("expected nonempty schema-1 plugin market index")
    assets = {INDEX: raw, LICENSES: regular_bytes(dist / LICENSES)}
    notices = zip_members(assets[LICENSES])
    required = {"LICENSE", "LICENSE.upstream", "THIRD_PARTY_NOTICES.md"}
    if not required <= notices.keys() or notices["LICENSE"] != license_text or not any(n.startswith("third_party/") for n in notices):
        raise PublishError("release license bundle is incomplete or unapproved")
    base = f"https://github.com/{repo}/releases/download/build-{source}/"
    seen_plugins = set()
    for plugin in index["plugins"]:
        identity = plugin.get("plugin_id")
        if not isinstance(identity, str) or identity in seen_plugins or not plugin.get("releases"):
            raise PublishError("duplicate or incomplete plugin index")
        seen_plugins.add(identity)
        for release in plugin["releases"]:
            manifest = release.get("manifest", {})
            if manifest.get("plugin_id") != identity or manifest.get("version") != release.get("version") or not release.get("artifacts"):
                raise PublishError("release/actual-worker manifest identity mismatch")
            for artifact in release["artifacts"]:
                filename = f'{identity}-{release["version"]}-linux-amd64.zip'
                if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.zip", filename) or filename in assets:
                    raise PublishError("ambiguous release asset name")
                if artifact.get("platform") != "linux-amd64" or artifact.get("format") != "zip" or artifact.get("url") != base + quote(filename, safe=""):
                    raise PublishError("artifact is not this source's Linux/amd64 release ZIP")
                payload = regular_bytes(dist / filename)
                if len(payload) != artifact.get("size") or sha256(payload) != artifact.get("sha256"):
                    raise PublishError("release ZIP size/SHA mismatch")
                members = zip_members(payload)
                inventory = artifact.get("files")
                if not isinstance(inventory, list) or len(inventory) != len(members) or {f.get("path") for f in inventory} != members.keys():
                    raise PublishError("ZIP and complete artifact.files inventory differ")
                for item in inventory:
                    value = members[item["path"]]
                    if len(value) != item.get("size") or sha256(value) != item.get("sha256"):
                        raise PublishError("ZIP member size/SHA mismatch")
                entry = manifest.get("entry")
                if entry not in members or sha256(members[entry]) != artifact.get("executable_sha256"):
                    raise PublishError("actual worker executable SHA mismatch")
                if not required <= members.keys() or members["LICENSE"] != license_text or not any(n.startswith("third_party/") for n in members):
                    raise PublishError("plugin archive has no approved complete license files")
                assets[filename] = payload
    if {p.name for p in dist.iterdir()} != assets.keys():
        raise PublishError("unexpected release output; refusing undeclared uploads")
    return assets


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo, self.token = repo, token
        self.opener = build_opener(NoRedirect())

    def _read(self, url, method="GET", data=None, headers=None, limit=4 << 20, redirects=False):
        headers = dict(headers or {})
        for _ in range(6):
            try:
                with self.opener.open(Request(url, data=data, headers=headers, method=method), timeout=60) as response:
                    raw = response.read(limit + 1)
                if len(raw) > limit:
                    raise PublishError("GitHub response exceeds expected bound")
                return raw
            except HTTPError as exc:
                location = exc.headers.get("Location", "")
                if redirects and method == "GET" and exc.code in {301, 302, 303, 307, 308}:
                    target = urlsplit(location)
                    if target.scheme != "https" or target.username or target.password or target.port not in {None, 443} or not (target.hostname == "github.com" or (target.hostname or "").endswith(".githubusercontent.com")):
                        raise PublishError("asset redirect leaves public GitHub delivery hosts") from None
                    # Never forward GITHUB_TOKEN to an asset CDN or redirect.
                    headers.pop("Authorization", None)
                    url = location
                    continue
                raise APIError(exc.code, method) from None
            except (URLError, TimeoutError, OSError):
                raise APIError(None, method) from None
        raise PublishError("asset redirect limit")

    def request(self, method: str, path: str, value=None, data=None, upload=False):
        if not path.startswith(f"/repos/{self.repo}/") and path != f"/repos/{self.repo}":
            raise PublishError("API request is outside this repository")
        headers = {"Authorization": "Bearer " + self.token, "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": API_VERSION, "User-Agent": "light-media-plugins-release"}
        if value is not None:
            data = json.dumps(value).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            headers["Content-Type"] = "application/octet-stream"
        return decode_json(self._read(("https://uploads.github.com" if upload else "https://api.github.com") + path, method, data, headers))

    def download(self, asset: dict, public: bool, expected_url: str) -> bytes:
        if asset.get("browser_download_url") != expected_url:
            raise PublishError("release asset download URL is not the expected public repository URL")
        headers = {"User-Agent": "light-media-plugins-release"}
        url = expected_url
        if not public:
            url = f'https://api.github.com/repos/{self.repo}/releases/assets/{int(asset["id"])}'
            headers.update({"Authorization": "Bearer " + self.token, "Accept": "application/octet-stream", "X-GitHub-Api-Version": API_VERSION})
        return self._read(url, headers=headers, limit=MAX_ASSET, redirects=True)


def maybe(api, path):
    try:
        return api.request("GET", path)
    except APIError as exc:
        if exc.status == 404:
            return None
        raise


def find_release(api, prefix: str, tag: str):
    release = maybe(api, prefix + "/releases/tags/" + tag)
    if release is not None:
        return release
    # The tag endpoint documents published releases only. Authenticated list
    # includes drafts, which lets an interrupted upload resume without duplicates.
    for page in range(1, 102):
        rows = api.request("GET", f"{prefix}/releases?per_page=100&page={page}")
        matches = [row for row in rows if row.get("tag_name") == tag]
        if len(matches) > 1:
            raise PublishError("ambiguous existing draft releases")
        if matches:
            return matches[0]
        if len(rows) < 100:
            return None
    raise PublishError("release pagination bound exceeded")


def head_snapshot(api, prefix: str, source: str):
    head = api.request("GET", prefix + "/git/ref/heads/main")["object"]["sha"]
    source_commit = api.request("GET", prefix + "/git/commits/" + source)
    current_commit = source_commit if head == source else api.request("GET", prefix + "/git/commits/" + head)
    source_tree = api.request("GET", prefix + "/git/trees/" + source_commit["tree"]["sha"])
    current_tree = source_tree if head == source else api.request("GET", prefix + "/git/trees/" + current_commit["tree"]["sha"])
    def entries(tree):
        if tree.get("truncated"):
            raise PublishError("cannot compare truncated source tree")
        return {x["path"]: (x["mode"], x["type"], x["sha"]) for x in tree["tree"]}
    original, current = entries(source_tree), entries(current_tree)
    if {k:v for k,v in original.items() if k != INDEX} != {k:v for k,v in current.items() if k != INDEX}:
        raise PublishError("main source changed; old build must not replace its index")
    return head, current_commit["tree"]["sha"], current, original


def list_assets(api, prefix: str, release_id: int) -> dict:
    out = {}
    for page in range(1, 102):
        rows = api.request("GET", f"{prefix}/releases/{release_id}/assets?per_page=100&page={page}")
        for asset in rows:
            if asset["name"] in out:
                raise PublishError("duplicate remote asset names")
            out[asset["name"]] = asset
        if len(rows) < 100:
            return out
    raise PublishError("release asset pagination bound exceeded")


def publish(root: Path, dist: Path, repo: str, source: str, api) -> dict:
    assets = validate_bundle(root, dist, repo, source)
    prefix, tag = f"/repos/{repo}", "build-" + source
    repository = api.request("GET", prefix)
    if repository.get("private") is not False or repository.get("default_branch") != "main" or repository.get("full_name", "").lower() != repo.lower():
        raise PublishError("publication requires this public repository with default main")
    _, _, _, original = head_snapshot(api, prefix, source)
    license_entry = original.get("LICENSE")
    if license_entry != ("100644", "blob", blob_sha(regular_bytes(root / "LICENSE"))):
        raise PublishError("approved local LICENSE does not match source commit")
    tag_ref = maybe(api, prefix + "/git/ref/tags/" + tag)
    if tag_ref and (tag_ref.get("object", {}).get("type") != "commit" or tag_ref["object"].get("sha") != source):
        raise PublishError("existing release tag points to a different source")
    release = find_release(api, prefix, tag)
    if release is None:
        try:
            release = api.request("POST", prefix + "/releases", {"tag_name": tag, "target_commitish": source, "name": tag, "body": "Linux amd64 plugins built from source commit " + source, "draft": True, "prerelease": False})
        except APIError as exc:
            if exc.status != 422:
                raise
            release = find_release(api, prefix, tag)
            if release is None:
                raise
    if release.get("tag_name") != tag or release.get("prerelease") or (release.get("draft") and release.get("target_commitish") != source):
        raise PublishError("existing release identity differs")
    release_id = int(release["id"])
    remote = list_assets(api, prefix, release_id)
    if not remote.keys() <= assets.keys():
        raise PublishError("release contains unexpected assets; nothing will be removed")
    base = f"https://github.com/{repo}/releases/download/{tag}/"
    for name, expected in assets.items():
        if name not in remote:
            try:
                remote[name] = api.request("POST", f"{prefix}/releases/{release_id}/assets?name={quote(name, safe='')}", data=expected, upload=True)
            except APIError as exc:
                if exc.status != 422:
                    raise
                # A concurrent identical upload is resolved by reads, not by
                # deleting an asset or blindly resubmitting an uncertain POST.
                remote = list_assets(api, prefix, release_id)
                if name not in remote:
                    raise
        asset = remote[name]
        if asset.get("state") != "uploaded" or asset.get("size") != len(expected) or asset.get("digest") not in {None, "sha256:" + sha256(expected)}:
            raise PublishError("existing asset metadata conflicts; refusing clobber")
        if api.download(asset, not release.get("draft", False), base + quote(name, safe="")) != expected:
            raise PublishError("downloaded asset bytes differ; refusing clobber")
    if release.get("draft"):
        release = api.request("PATCH", f"{prefix}/releases/{release_id}", {"draft": False})
        if release.get("draft") is not False:
            raise PublishError("release publication was not confirmed")
    tag_ref = api.request("GET", prefix + "/git/ref/tags/" + tag)
    if tag_ref.get("object", {}).get("type") != "commit" or tag_ref["object"].get("sha") != source:
        raise PublishError("published tag does not identify built source")
    # Verify the *public* downloads too, before making the install index visible.
    for name, expected in assets.items():
        actual = api.download(remote[name], True, base + quote(name, safe=""))
        if actual != expected or sha256(actual) != sha256(expected):
            raise PublishError("public release download bytes/SHA not verified")
    head, tree, entries, _ = head_snapshot(api, prefix, source)
    current = None
    if INDEX in entries:
        if entries[INDEX][0:2] != ("100644", "blob"):
            raise PublishError("root index is not an ordinary file")
        obj = api.request("GET", prefix + "/git/blobs/" + entries[INDEX][2])
        if obj.get("encoding") != "base64":
            raise PublishError("unsupported root index encoding")
        current = base64.b64decode(obj["content"])
    if current == assets[INDEX]:
        final = head
    else:
        blob = api.request("POST", prefix + "/git/blobs", {"content": base64.b64encode(assets[INDEX]).decode(), "encoding": "base64"})
        updated_tree = api.request("POST", prefix + "/git/trees", {"base_tree": tree, "tree": [{"path": INDEX, "mode": "100644", "type": "blob", "sha": blob["sha"]}]})
        commit = api.request("POST", prefix + "/git/commits", {"message": "chore: publish plugin index for " + source + " [skip ci]", "tree": updated_tree["sha"], "parents": [head]})
        final = commit["sha"]
        result = api.request("PATCH", prefix + "/git/refs/heads/main", {"sha": final, "force": False})
        if result.get("object", {}).get("sha") != final:
            raise PublishError("index ref update not confirmed")
    observed = api.request("GET", prefix + "/git/ref/heads/main")["object"]["sha"]
    if observed != final:
        raise PublishError("main advanced during final readback; no overwrite retry")
    return {"source_commit": source, "release_tag": tag, "index_commit": final, "observed_main": observed, "assets": {name: sha256(value) for name, value in assets.items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args(argv)
    try:
        if os.environ.get("GITHUB_ACTIONS") != "true" or os.environ.get("GITHUB_REF") != "refs/heads/main" or os.environ.get("GITHUB_EVENT_NAME") not in {"push", "workflow_dispatch"} or os.environ.get("GITHUB_SHA") != args.source_sha or os.environ.get("GITHUB_REPOSITORY") != args.repo:
            raise PublishError("release is restricted to this repository's main push/manual workflow")
        root = Path(__file__).resolve().parents[1]
        validate_bundle(root, args.dist, args.repo, args.source_sha)
        token = os.environ.get("GITHUB_TOKEN", "")
        if not token:
            raise PublishError("ephemeral workflow GITHUB_TOKEN is required")
        result = publish(root, args.dist, args.repo, args.source_sha, GitHub(args.repo, token))
        print(json.dumps(result, sort_keys=True))
        return 0
    except (PublishError, OSError, KeyError, TypeError, ValueError) as exc:
        # Never print remote response bodies, headers, redirect URLs or tokens.
        message = str(exc) if isinstance(exc, PublishError) else type(exc).__name__
        print("release failed: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
