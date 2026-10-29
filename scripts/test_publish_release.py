"""Controlled, token-free API tests; no remote workflow/release is executed."""
import base64
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
import zipfile

import publish_release as release

REPO = "owned/controlled-plugins"
SOURCE = "a" * 40
BASE = f"https://github.com/{REPO}/releases/download/build-{SOURCE}/"
# Shape observed on the first real GitHub draft release, before publication.
DRAFT_BASE = f"https://github.com/{REPO}/releases/download/untagged-57fb3b676a90605f3dbe/"


def archive(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)
    return output.getvalue()


class ControlledGitHub:
    """Minimal native GitHub API contract with an independently enforced DAG CAS."""
    def __init__(self, license_bytes):
        self.calls, self.downloads, self.download_metadata = [], [], []
        self.private, self.default = False, "main"
        self.head = SOURCE
        self.source_tree = "b" * 40
        self.commits = {SOURCE: {"tree": {"sha": self.source_tree}, "parents": []}}
        self.trees = {self.source_tree: {"LICENSE": ("100644", "blob", release.blob_sha(license_bytes)), "cmd": ("040000", "tree", "c" * 40)}}
        self.blobs = {}
        self.release = None
        self.assets, self.payloads = {}, {}
        self.tag = None
        self.lose_upload = self.conflict_upload = False
        self.corrupt_public = self.race_at_ref = self.advance_after_upload = False
        self.deny_create = False
        self.published_asset_override = None

    def newer_source(self):
        head, tree = "d" * 40, "e" * 40
        self.trees[tree] = {**self.trees[self.source_tree], "cmd": ("040000", "tree", "f" * 40)}
        self.commits[head] = {"tree": {"sha": tree}, "parents": [self.head]}
        self.head = head

    def writes(self):
        return [call for call in self.calls if call[0] != "GET"]

    def request(self, method, path, value=None, data=None, upload=False):
        self.calls.append((method, path, copy.deepcopy(value), data, upload))
        route = path.removeprefix("/repos/" + REPO)
        if method == "GET" and route == "":
            return {"private": self.private, "default_branch": self.default, "full_name": REPO}
        if method == "GET" and route == "/git/ref/heads/main":
            return {"object": {"type": "commit", "sha": self.head}}
        if method == "GET" and route.startswith("/git/ref/tags/"):
            if self.tag is None:
                raise release.APIError(404, "GET")
            return {"object": {"type": "commit", "sha": self.tag}}
        if method == "GET" and route.startswith("/git/commits/"):
            return copy.deepcopy(self.commits[route.rsplit("/", 1)[1]])
        if method == "GET" and route.startswith("/git/trees/"):
            entries = self.trees[route.rsplit("/", 1)[1]]
            return {"truncated": False, "tree": [{"path": p, "mode": v[0], "type": v[1], "sha": v[2]} for p, v in entries.items()]}
        if method == "GET" and route.startswith("/releases/tags/"):
            if self.release is None or self.release["draft"]:
                raise release.APIError(404, "GET")
            return copy.deepcopy(self.release)
        if method == "GET" and route.startswith("/releases?"):
            return [] if self.release is None else [copy.deepcopy(self.release)]
        if method == "GET" and route.startswith("/releases/1/assets?"):
            return list(copy.deepcopy(self.assets).values())
        if method == "POST" and route == "/releases":
            if self.deny_create:
                raise release.APIError(403, "POST")
            if self.release:
                raise AssertionError("existing draft must be found, not recreated")
            self.release = {"id": 1, **value}
            return copy.deepcopy(self.release)
        if method == "POST" and route.startswith("/releases/1/assets?"):
            assert upload is True
            name = parse_qs(urlsplit(path).query)["name"][0]
            if name in self.assets:
                raise AssertionError("asset clobber/duplicate POST")
            self.payloads[name] = data
            self.assets[name] = {"id": len(self.assets)+1, "name": name, "size": len(data), "digest": "sha256:"+release.sha256(data), "state": "uploaded", "browser_download_url": (DRAFT_BASE if self.release["draft"] else BASE)+name}
            if self.lose_upload:
                self.lose_upload = False
                raise release.APIError(None, "POST")
            if self.conflict_upload:
                self.conflict_upload = False
                raise release.APIError(422, "POST")
            return copy.deepcopy(self.assets[name])
        if method == "PATCH" and route == "/releases/1":
            assert value == {"draft": False}
            self.release["draft"] = False
            for name, asset in self.assets.items():
                asset["browser_download_url"] = BASE+name
            if self.published_asset_override:
                self.assets[release.INDEX].update(self.published_asset_override)
            self.tag = SOURCE
            if self.advance_after_upload:
                self.newer_source()
            return copy.deepcopy(self.release)
        if method == "POST" and route == "/git/blobs":
            content = base64.b64decode(value["content"])
            sha = release.blob_sha(content)
            self.blobs[sha] = content
            return {"sha": sha}
        if method == "GET" and route.startswith("/git/blobs/"):
            content = self.blobs[route.rsplit("/", 1)[1]]
            return {"encoding": "base64", "content": base64.b64encode(content).decode()}
        if method == "POST" and route == "/git/trees":
            assert len(value["tree"]) == 1 and value["tree"][0]["path"] == release.INDEX
            item = value["tree"][0]
            sha = release.sha256(json.dumps(value, sort_keys=True).encode())[:40]
            self.trees[sha] = {**self.trees[value["base_tree"]], release.INDEX: (item["mode"], item["type"], item["sha"])}
            return {"sha": sha}
        if method == "POST" and route == "/git/commits":
            sha = release.sha256(json.dumps(value, sort_keys=True).encode())[:40]
            self.commits[sha] = {"tree": {"sha": value["tree"]}, "parents": value["parents"]}
            return {"sha": sha}
        if method == "PATCH" and route == "/git/refs/heads/main":
            assert value["force"] is False
            if self.race_at_ref:
                self.newer_source()
            target = self.commits[value["sha"]]
            if target["parents"] != [self.head]:
                raise release.APIError(422, "PATCH")
            self.head = value["sha"]
            return {"object": {"sha": self.head}}
        raise AssertionError((method, path, value))

    def download(self, asset, public, expected_url):
        self.downloads.append((asset["name"], public))
        self.download_metadata.append((asset["name"], public, asset["browser_download_url"], asset["id"]))
        assert expected_url == BASE+asset["name"]
        if public:
            assert self.release["draft"] is False
            assert asset["browser_download_url"] == expected_url, "publisher retained stale draft URL instead of refreshing metadata"
        else:
            assert asset["browser_download_url"] == DRAFT_BASE+asset["name"]
        data = self.payloads[asset["name"]]
        return data+b"corruption" if public and self.corrupt_public else data


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dist = self.root/"dist"
        self.dist.mkdir()
        self.license = b"Owned synthetic test license; no public license is approved by this fixture.\n"
        (self.root/"LICENSE").write_bytes(self.license)
        notices = {"LICENSE": self.license, "LICENSE.upstream": b"synthetic upstream license", "THIRD_PARTY_NOTICES.md": b"synthetic notices", "third_party/license": b"synthetic third party"}
        files = {"category-editor": b"synthetic worker bytes for packaging validation only", **notices}
        self.plugin_name = "CategoryEditor-1.3-linux-amd64.zip"
        binary = archive(files)
        (self.dist/self.plugin_name).write_bytes(binary)
        (self.dist/release.LICENSES).write_bytes(archive(notices))
        artifact = {"platform": "linux-amd64", "format": "zip", "url": BASE+self.plugin_name, "sha256": release.sha256(binary), "size": len(binary), "executable_sha256": release.sha256(files["category-editor"]), "files": [{"path": n, "size": len(b), "sha256": release.sha256(b)} for n,b in files.items()]}
        self.index = {"schema_version": 1, "plugins": [{"plugin_id": "CategoryEditor", "current_version": "1.3", "releases": [{"version": "1.3", "manifest": {"plugin_id": "CategoryEditor", "version": "1.3", "entry": "category-editor"}, "artifacts": [artifact]}]}]}
        self.save_index()
        self.api = ControlledGitHub(self.license)

    def save_index(self):
        (self.dist/release.INDEX).write_text(json.dumps(self.index))

    def run_publish(self):
        return release.publish(self.root, self.dist, REPO, SOURCE, self.api)

    def test_success_all_bytes_publicly_verified_before_index_cas_and_rerun_noop(self):
        first = self.run_publish()
        self.assertEqual(first["index_commit"], self.api.head)
        self.assertEqual(first["observed_main"], self.api.head)
        self.assertEqual(first["release_tag"], "build-"+SOURCE)
        self.assertEqual(set(first["assets"]), {release.INDEX, release.LICENSES, self.plugin_name})
        self.assertEqual({n for n,p in self.api.downloads if p}, set(first["assets"]))
        writes = len(self.api.writes())
        second = self.run_publish()
        self.assertEqual(first, second)
        self.assertEqual(len(self.api.writes()), writes, "idempotent rerun must not create/delete/upload/update anything")
        self.assertFalse(any(c[0] == "DELETE" for c in self.api.calls))

    def test_real_untagged_draft_refreshes_published_metadata_before_public_download(self):
        self.run_publish()
        draft_reads = [(n, url, asset_id) for n, public, url, asset_id in self.api.download_metadata if not public]
        public_reads = [(n, url, asset_id) for n, public, url, asset_id in self.api.download_metadata if public]
        self.assertEqual(len(draft_reads), 3)
        self.assertEqual({n: i for n, _, i in draft_reads}, {n: i for n, _, i in public_reads})
        self.assertTrue(all(url == DRAFT_BASE+n for n, url, _ in draft_reads))
        self.assertTrue(all(url == BASE+n for n, url, _ in public_reads))
        publication = next(i for i,c in enumerate(self.api.calls) if c[0] == "PATCH" and c[1].endswith("/releases/1"))
        refresh = next(i for i,c in enumerate(self.api.calls) if i > publication and c[0] == "GET" and "/releases/1/assets?" in c[1])
        index_write = next(i for i,c in enumerate(self.api.calls) if c[0] == "POST" and c[1].endswith("/git/blobs"))
        self.assertLess(publication, refresh)
        self.assertLess(refresh, index_write)

    def test_published_asset_identity_size_or_digest_change_blocks_index(self):
        for altered in [{"id": 999}, {"size": 1}, {"digest": "sha256:"+"0"*64}]:
            with self.subTest(altered=altered):
                self.api = ControlledGitHub(self.license)
                self.api.published_asset_override = altered
                with self.assertRaises(release.PublishError): self.run_publish()
                self.assertEqual(self.api.head, SOURCE)
                self.assertFalse(any(c[0] == "POST" and c[1].endswith("/git/blobs") for c in self.api.calls))

    def test_interrupted_applied_upload_resumes_existing_draft_without_resubmit(self):
        self.api.lose_upload = True
        with self.assertRaises(release.APIError): self.run_publish()
        self.assertEqual(self.api.head, SOURCE)
        self.assertTrue(self.api.release["draft"])
        self.run_publish()
        uploads = [c for c in self.api.calls if c[0] == "POST" and c[4]]
        self.assertEqual(len(uploads), 3)
        self.assertEqual(len({c[1] for c in uploads}), 3)

    def test_concurrent_asset_creation_only_reads_back_422(self):
        self.api.conflict_upload = True
        self.run_publish()
        self.assertEqual(len([c for c in self.api.calls if c[0] == "POST" and c[4]]), 3)

    def test_conflicting_existing_asset_is_not_clobbered(self):
        self.run_publish()
        self.api.payloads[self.plugin_name] += b"different remote bytes"
        writes = len(self.api.writes())
        with self.assertRaisesRegex(release.PublishError, "bytes differ"): self.run_publish()
        self.assertEqual(len(self.api.writes()), writes)

    def test_corrupt_public_download_blocks_index(self):
        self.api.corrupt_public = True
        with self.assertRaisesRegex(release.PublishError, "public release"): self.run_publish()
        self.assertEqual(self.api.head, SOURCE)
        self.assertFalse(any("/git/blobs" in c[1] and c[0] == "POST" for c in self.api.calls))

    def test_source_change_before_release_blocks_all_writes(self):
        self.api.newer_source()
        with self.assertRaisesRegex(release.PublishError, "main source changed"): self.run_publish()
        self.assertEqual(self.api.writes(), [])

    def test_source_change_after_assets_blocks_index(self):
        self.api.advance_after_upload = True
        with self.assertRaisesRegex(release.PublishError, "main source changed"): self.run_publish()
        self.assertEqual(self.api.head, "d"*40)
        self.assertFalse(any("/git/blobs" in c[1] and c[0] == "POST" for c in self.api.calls))

    def test_true_head_cas_race_rejects_and_never_force_retries(self):
        self.api.race_at_ref = True
        with self.assertRaises(release.APIError): self.run_publish()
        refs = [c for c in self.api.calls if c[0] == "PATCH" and c[1].endswith("/git/refs/heads/main")]
        self.assertEqual(len(refs), 1)
        self.assertIs(refs[0][2]["force"], False)
        self.assertEqual(self.api.head, "d"*40)

    def test_missing_root_license_fails_before_network(self):
        (self.root/"LICENSE").rename(self.root/"NOT_LICENSE")
        with self.assertRaises(release.PublishError): self.run_publish()
        self.assertEqual(self.api.calls, [])

    def test_source_license_must_match_approved_local_bytes(self):
        self.api.trees[self.api.source_tree]["LICENSE"] = ("100644", "blob", "0"*40)
        with self.assertRaisesRegex(release.PublishError, "LICENSE does not match"): self.run_publish()
        self.assertEqual(self.api.writes(), [])

    def test_probe_without_root_license_in_zip_is_not_publishable(self):
        archive_bytes = (self.dist/release.LICENSES).read_bytes()
        members = release.zip_members(archive_bytes)
        members.pop("LICENSE")
        (self.dist/release.LICENSES).write_bytes(archive(members))
        with self.assertRaisesRegex(release.PublishError, "license bundle"): self.run_publish()
        self.assertEqual(self.api.calls, [])

    def test_wrong_source_asset_url_fails_before_network(self):
        self.index["plugins"][0]["releases"][0]["artifacts"][0]["url"] = "https://other.invalid/plugin.zip"
        self.save_index()
        with self.assertRaises(release.PublishError): self.run_publish()
        self.assertEqual(self.api.calls, [])

    def test_private_or_wrong_default_branch_is_rejected(self):
        for name, value in [("private", True), ("default", "other")]:
            with self.subTest(name=name):
                api = ControlledGitHub(self.license)
                setattr(api, name, value)
                with self.assertRaises(release.PublishError): release.publish(self.root, self.dist, REPO, SOURCE, api)
                self.assertEqual(api.writes(), [])

    def test_403_never_retries_or_escalates_permissions(self):
        self.api.deny_create = True
        with self.assertRaises(release.APIError) as caught: self.run_publish()
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(len(self.api.writes()), 1)
        self.assertEqual(self.api.head, SOURCE)

    def test_different_existing_tag_is_rejected_before_upload(self):
        self.api.tag = "f"*40
        with self.assertRaisesRegex(release.PublishError, "tag points"): self.run_publish()
        self.assertEqual(self.api.writes(), [])

    def test_cli_rejects_pr_or_non_main_before_reading_token(self):
        for event, ref in [("pull_request", "refs/pull/1/merge"), ("workflow_dispatch", "refs/heads/topic")]:
            env = {"GITHUB_ACTIONS": "true", "GITHUB_REF": ref, "GITHUB_EVENT_NAME": event, "GITHUB_SHA": SOURCE, "GITHUB_REPOSITORY": REPO, "GITHUB_TOKEN": "NEVER_PRINT_THIS"}
            with patch.dict("os.environ", env, clear=True), patch("sys.stderr", new_callable=io.StringIO) as err:
                self.assertEqual(release.main(["--dist", str(self.dist), "--repo", REPO, "--source-sha", SOURCE]), 1)
                self.assertNotIn("NEVER_PRINT_THIS", err.getvalue())


class TransportTests(unittest.TestCase):
    def test_authenticated_asset_redirect_drops_token(self):
        api = release.GitHub(REPO, "owned-test-token")
        calls = []
        class Response(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self, *args): self.close()
        class Opener:
            def open(self, req, timeout):
                calls.append(req)
                if len(calls) == 1:
                    raise HTTPError(req.full_url, 302, "redirect", {"Location": "https://release-assets.githubusercontent.com/owned/download?signature=synthetic"}, None)
                return Response(b"owned bytes")
        api.opener = Opener()
        asset = {"id": 7, "browser_download_url": DRAFT_BASE+"owned.zip"}
        self.assertEqual(api.download(asset, False, BASE+"owned.zip"), b"owned bytes")
        self.assertEqual(calls[0].full_url, f"https://api.github.com/repos/{REPO}/releases/assets/7")
        self.assertEqual(calls[0].get_header("Authorization"), "Bearer owned-test-token")
        self.assertIsNone(calls[1].get_header("Authorization"))

    def test_draft_browser_url_is_never_followed_and_public_still_requires_canonical_url(self):
        api = release.GitHub(REPO, "owned-test-token")
        asset = {"id": 7, "browser_download_url": "https://unrelated.invalid/never-follow"}
        with patch.object(api, "_read", return_value=b"owned") as read:
            self.assertEqual(api.download(asset, False, BASE+"owned.zip"), b"owned")
            self.assertEqual(read.call_args.args[0], f"https://api.github.com/repos/{REPO}/releases/assets/7")
            read.reset_mock()
            with self.assertRaisesRegex(release.PublishError, "public repository URL"):
                api.download(asset, True, BASE+"owned.zip")
            read.assert_not_called()
        for identity in ["7", 0, -1, True, "../foreign"]:
            with self.subTest(identity=identity), patch.object(api, "_read") as read:
                with self.assertRaisesRegex(release.PublishError, "invalid identity"):
                    api.download({"id": identity}, False, BASE+"owned.zip")
                read.assert_not_called()

    def test_asset_redirect_to_unrelated_host_is_blocked(self):
        api = release.GitHub(REPO, "owned-test-token")
        class Opener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 302, "redirect", {"Location": "https://unrelated.invalid/steal"}, None)
        api.opener = Opener()
        with self.assertRaisesRegex(release.PublishError, "delivery hosts"):
            api.download({"id": 7, "browser_download_url": BASE+"owned.zip"}, False, BASE+"owned.zip")


if __name__ == "__main__":
    unittest.main()
