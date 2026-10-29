#!/usr/bin/env python3
"""Packaging tests use synthetic asset trees, not a real Vue/browser acceptance."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

spec = importlib.util.spec_from_file_location("build_plugins", Path(__file__).with_name("build_plugins.py"))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def manifest(frontend=False):
    value = {"schema_version": 1, "plugin_id": "OwnedFixture", "name": "Owned fixture", "version": "1.2.3", "runtime": "go-executable", "entry": "owned-worker", "host_api_min": 1, "host_api_max": 1, "methods": ["init", "get_state", "get_service", "get_command", "stop"], "capabilities": []}
    if frontend:
        value["frontend"] = {"contract": "light-media.vue-federation/v1", "root": "frontend/assets", "entry": "remoteEntry.js", "exposes": ["Config"], "shared": ["vue"], "api_contract": "light-media.plugin-api/v1"}
    return value


def fixture_tree(root):
    (root / "fonts").mkdir(parents=True)
    values = {
        "remoteEntry.js": b'export const init=()=>{}; export const get=()=>import("./lazy.js");',
        "lazy.js": b'import "./style.css"; export default {setup(){}};',
        "style.css": b'@font-face{src:url("./fonts/owned.woff2")} .owned{background:url(./image.png)}',
        "fonts/owned.woff2": b"synthetic-font",
        "image.png": b"synthetic-image-not-browser-fixture",
        "unreferenced-but-built.js": b"export const retained=true;",
    }
    for name, data in values.items():
        (root / name).write_bytes(data)
    return values


class BuildPackagingTests(unittest.TestCase):
    def test_frontend_full_tree_including_chunks_css_fonts_and_unreferenced_assets(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            want = fixture_tree(root)
            got = builder.collect_frontend(root, manifest(True)["frontend"])
            self.assertEqual(got, want)
            files = {"owned-worker": b"synthetic executable", **{"frontend/assets/" + k: v for k, v in got.items()}, "LICENSE": b"owned license"}
            archive = root / "owned.zip"
            builder.archive_plugin(archive, files)
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(set(zipped.namelist()), set(files))
                self.assertEqual(zipped.read("frontend/assets/lazy.js"), want["lazy.js"])
                for member in zipped.infolist():
                    self.assertTrue(stat.S_ISREG(member.external_attr >> 16))

    def test_missing_lazy_chunk_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture_tree(root)
            (root / "lazy.js").unlink()
            with self.assertRaisesRegex(builder.BuildError, "missing asset: lazy.js"):
                builder.collect_frontend(root, manifest(True)["frontend"])

    def test_missing_remote_entry_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "other.js").write_text("export default {}")
            with self.assertRaisesRegex(builder.BuildError, "manifest entry"):
                builder.collect_frontend(root, manifest(True)["frontend"])

    def test_symlink_outside_tree_and_symlink_directory_rejected(self):
        for directory_link in (False, True):
            with self.subTest(directory=directory_link), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "output"
                output.mkdir()
                fixture_tree(output)
                (root / "outside.js").write_text("private unrelated bytes")
                (output / "escape").symlink_to(root if directory_link else root / "outside.js", target_is_directory=directory_link)
                with self.assertRaisesRegex(builder.BuildError, "symlink"):
                    builder.collect_frontend(output, manifest(True)["frontend"])

    def test_parent_escape_absolute_and_remote_graph_rejected(self):
        for target in ("../../outside.js", "/assets/lazy.js", "https://example.invalid/lazy.js", "./lazy.js?v=1"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "remoteEntry.js").write_text(f'export const get=()=>import({json.dumps(target)});')
                with self.assertRaises(builder.BuildError):
                    builder.collect_frontend(root, manifest(True)["frontend"])

    def test_frontend_requires_real_build_command_and_isolated_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            front = manifest(True)["frontend"]
            for config in ({}, {"frontend": {"command": ["true"], "cwd": ".", "output": "built"}}, {"frontend": {"command": ["echo", "{output}"], "cwd": ".", "output": "../outside"}}):
                with self.assertRaises(builder.BuildError):
                    builder.build_frontend(root, build, config, front, dict(os.environ))

    def test_actual_synthetic_frontend_build_command_output_is_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            build = root / "build"
            build.mkdir()
            program = root / "synthetic_frontend.py"
            program.write_text('from pathlib import Path\nimport sys\np=Path(sys.argv[1]);p.mkdir();(p/"remoteEntry.js").write_text(\'export const get=()=>import("./chunk.js");\');(p/"chunk.js").write_text("export default {setup(){}};")\n')
            config = {"frontend": {"command": [sys.executable, str(program), "{output}"], "cwd": ".", "output": "built-assets"}}
            got = builder.build_frontend(root, build, config, manifest(True)["frontend"], dict(os.environ))
            self.assertEqual(set(got), {"remoteEntry.js", "chunk.js"})

    def test_manifest_entry_preserved_and_frontend_abi_checked(self):
        value = manifest()
        value["entry"] = "category-editor"
        result = builder.validate_manifest(json.dumps(value).encode(), "OwnedFixture")
        self.assertEqual(result["entry"], "category-editor")
        value = manifest(True)
        value["frontend"]["entry"] = "index.js"
        with self.assertRaises(builder.BuildError):
            builder.validate_manifest(json.dumps(value).encode(), "OwnedFixture")

    def test_explicit_release_https_only(self):
        self.assertEqual(builder.release_base("https://github.com/owner/repo/releases/download/build-abc"), "https://github.com/owner/repo/releases/download/build-abc/")
        for value in ("http://example.invalid", "https://user:secret@example.invalid/", "https://example.invalid/?secret=x", "https://example.invalid/#tag", "https://example.invalid:broken/", "https:///missing", "https://example.invalid/\n"):
            with self.subTest(value=value), self.assertRaises(builder.BuildError):
                builder.release_base(value)

    def test_existing_output_and_publish_race_never_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "dist"
            output.mkdir()
            keep = output / "go-plugins.v1.json"
            keep.write_bytes(b"unknown existing bytes")
            with self.assertRaises(builder.BuildError):
                builder.fresh_output(output)
            with self.assertRaises(FileExistsError):
                builder.publish_fresh(output, [], {"schema_version": 1, "plugins": []})
            self.assertEqual(keep.read_bytes(), b"unknown existing bytes")
            alias = root / "alias"
            alias.symlink_to(output, target_is_directory=True)
            with self.assertRaises(builder.BuildError):
                builder.fresh_output(alias / "nested")

    def test_inventory_rejects_collisions_receipts_and_unsafe_paths(self):
        for name in ("../secret", "/absolute", ".acquired.json", "./foo", "A/../B", "C:/x", "foo\\bar", ".", "NUL.txt"):
            with self.subTest(name=name), self.assertRaises(builder.BuildError):
                builder.add_file({}, name, b"owned")
        for names in (("A.js", "a.js"), ("fonts/a.woff", "Fonts/b.woff"), ("dir", "dir/file.js")):
            with self.subTest(names=names):
                files = {}
                builder.add_file(files, names[0], b"owned")
                with self.assertRaises(builder.BuildError):
                    builder.add_file(files, names[1], b"owned")

    def test_real_command_arguments_and_exact_index_hashes(self):
        # The Go command is stubbed here only to inspect build flags. It produces
        # a clearly synthetic executable fixture; the real CategoryEditor build
        # and --manifest are verified separately by the local build invocation.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "cmd/owned").mkdir(parents=True)
            build = root / "build"
            build.mkdir()
            (root / "LICENSE").write_text("synthetic-license")
            (root / "LICENSE.upstream").write_text("synthetic-upstream")
            got_commands = []
            value = manifest()
            def fake_command(argv, cwd, env, timeout=600):
                got_commands.append(argv)
                self.assertEqual((env["GOOS"], env["GOARCH"], env["CGO_ENABLED"]), ("linux", "amd64", "0"))
                if argv[1] == "build":
                    Path(argv[argv.index("-o") + 1]).write_bytes(b"synthetic-worker")
                    return b""
                self.assertEqual(argv[1:], ["--manifest"])
                return json.dumps(value).encode()
            conf = {"id": "OwnedFixture", "package": "./cmd/owned", "host_contract": "light-media.sdk-base/v1", "license_files": ["LICENSE.upstream"]}
            with mock.patch.object(builder, "command", side_effect=fake_command):
                index, archive = builder.build_plugin(root, build, conf, "https://example.invalid/releases/test/", "owned-go")
            self.assertIn("-trimpath", got_commands[0])
            self.assertIn("-buildvcs=false", got_commands[0])
            artifact = index["releases"][0]["artifacts"][0]
            self.assertEqual(artifact["sha256"], builder.digest(archive.read_bytes()))
            self.assertEqual(artifact["size"], archive.stat().st_size)
            self.assertEqual(artifact["executable_sha256"], builder.digest(b"synthetic-worker"))
            with zipfile.ZipFile(archive) as zipped:
                for file in artifact["files"]:
                    content = zipped.read(file["path"])
                    self.assertEqual(file["size"], len(content))
                    self.assertEqual(file["sha256"], builder.digest(content))
                self.assertEqual(set(zipped.namelist()), {"owned-worker", "LICENSE", "LICENSE.upstream"})
            self.assertNotIn("package_sha256", artifact)
            self.assertEqual(artifact["url"], "https://example.invalid/releases/test/OwnedFixture-1.2.3-linux-amd64.zip")

class LicenseBundleTests(unittest.TestCase):
    def test_release_requires_root_license_and_probe_is_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE.upstream").write_text("upstream license")
            specs = [{"license_files": ["LICENSE.upstream"]}]
            with self.assertRaisesRegex(builder.BuildError, "LICENSE"):
                builder.license_inventory(root, specs)
            self.assertEqual(set(builder.license_inventory(root, specs, local_probe=True)), {"LICENSE.upstream"})
            (root / "LICENSE").write_text("authorized release license")
            files = builder.license_inventory(root, specs)
            self.assertEqual(set(files), {"LICENSE", "LICENSE.upstream"})
            archive = root / "THIRD_PARTY_LICENSES.zip"
            builder.archive_plugin(archive, files)
            with zipfile.ZipFile(archive) as zipped:
                self.assertEqual(set(zipped.namelist()), {"LICENSE", "LICENSE.upstream"})


if __name__ == "__main__":
    unittest.main()
