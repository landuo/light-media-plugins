#!/usr/bin/env python3
"""Build the local independently-reviewed parent0300 host through minimal Git-blob overlays in its worktree."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import subprocess

HOST = Path('/Users/accidia/projects/light-media')
OUT = Path(__file__).resolve().parent
REV = '0719a221229b32270e93d52ee917813258d3aa49'

def git(*args):
    return subprocess.check_output(['git', *args], cwd=HOST)

def sha(data):
    return hashlib.sha256(data).hexdigest()

def objects(raw):
    decoder = json.JSONDecoder()
    text = raw.decode()
    result = []
    while text.strip():
        text = text.lstrip()
        obj, used = decoder.raw_decode(text)
        result.append(obj)
        text = text[used:]
    return result

tree = {}
for record in git('ls-tree', '-rz', '--full-tree', REV).split(b'\0'):
    if record:
        header, path = record.split(b'\t', 1)
        mode, kind, blob = header.split()
        assert kind == b'blob', (path, kind)
        tree[path.decode()] = blob.decode()

# The existing module/lock inputs are already exactly the local independently-reviewed parent0300 host's.
# No alternate project checkout, source copy, module replacement or cache exists.
for name in ['go.mod', 'go.sum']:
    assert (HOST / name).read_bytes() == git('show', f'{REV}:{name}'), name

# Freeze only the reviewed-in-progress finite PUI increment. This is not a
# Git revision or Main acceptance of those primitives.
pui_manifest = Path('/Users/accidia/projects/light-media/work/pluginuninstall-source-startup-20261105/host-files-current.json')
pui_record = json.loads(pui_manifest.read_text())
pui = {}
pui_sources = OUT / 'pui-frozen-files'
for entry in pui_record['files']:
    original = Path(entry['path'])
    relative = str(original.relative_to(HOST))
    data = original.read_bytes()
    assert sha(data) == entry['sha256'], relative
    pui[relative] = entry['sha256']
    dest = pui_sources / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
replace = {}
changed = set(filter(None, git('diff', '--name-only', '-z', REV).decode().split('\0')))
untracked = set(filter(None, git('ls-files', '--others', '--exclude-standard', '-z').decode().split('\0')))
# The concurrently developed PluginUnInstall additions must not enter this old build,
# even if a new file appears between the first inventory and compilation.
untracked.update([
    'internal/plugins/cleanup_continuation.go',
    'internal/app/plugin_original_cleanup_submitted.go',
    'internal/app/plugin_original_host_manager_source.go',
    'internal/app/plugin_original_operation_lease.go',
])
overlay_files = OUT / 'host-pluginuninstall-reviewed-minimal-overlay'
overlay_files.mkdir(exist_ok=True)
for name in sorted(changed | untracked):
    # Only compile/embedded inputs need an overlay; not documentation/evidence.
    if not (name.endswith('.go') or name.startswith('internal/webui/') or name.startswith('third_party/')):
        continue
    if name in pui:
        replace[str(HOST / name)] = str(pui_sources / name)
        continue
    if name in tree:
        data = git('show', f'{REV}:{name}')
        dest = overlay_files / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        replace[str(HOST / name)] = str(dest)
    else:
        replace[str(HOST / name)] = ''
overlay = OUT / 'host-pluginuninstall-reviewed-overlay.json'
overlay.write_text(json.dumps({'Replace': replace}, indent=2) + '\n')
env = {**os.environ, 'CGO_ENABLED': '0', 'GOOS': 'linux', 'GOARCH': 'amd64'}
list_cmd = ['go', 'list', f'-overlay={overlay}', '-deps', '-json', './cmd/server']

def snapshot():
    completed = subprocess.run(list_cmd, cwd=HOST, env=env, capture_output=True)
    assert completed.returncode == 0, completed.stderr.decode()
    inputs = {}
    for package in objects(completed.stdout):
        directory = Path(package['Dir'])
        if not directory.is_relative_to(HOST):
            continue
        for field in ['GoFiles', 'CgoFiles', 'SFiles', 'EmbedFiles']:
            for leaf in package.get(field, []):
                original = directory / leaf
                relative = str(original.relative_to(HOST))
                assert relative in tree or relative in pui, relative
                actual = Path(replace.get(str(original), str(original)))
                data = actual.read_bytes()
                blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                if relative in pui:
                    assert sha(data) == pui[relative], relative
                else:
                    assert blob == tree[relative], relative
                inputs[relative] = {'sha256': sha(data), 'git_blob': tree.get(relative), 'actual_blob': blob,
                                    'frozen_PUI_increment': relative in pui, 'overlay': str(original) in replace}
    for name in ['go.mod', 'go.sum']:
        data = (HOST / name).read_bytes()
        inputs[name] = {'sha256': sha(data), 'git_blob': tree[name], 'overlay': False}
    return inputs

before = snapshot()
binary = OUT / 'light-media-host-pluginuninstall-reviewed-linux'
cmd = ['go', 'build', '-trimpath', '-buildvcs=false', f'-overlay={overlay}', '-o', str(binary), './cmd/server']
completed = subprocess.run(cmd, cwd=HOST, env=env, capture_output=True)
(OUT / 'host-pluginuninstall-reviewed-build.log').write_bytes(completed.stdout + completed.stderr)
after = snapshot()
result = {'classification': 'actual compile-only candidate base0719 parent0300 plus independently-reviewed finite PUI19/f9e4 increment (source/App f38f); ordinary Main/UI still pending. Minimal overlays in original worktree; no new checkout/source clone',
          'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'base_revision': REV, 'frozen_PUI_manifest_sha256': sha(pui_manifest.read_bytes()), 'frozen_PUI_files': pui, 'command': cmd, 'exit_code': completed.returncode,
          'environment': {k: env[k] for k in ['CGO_ENABLED', 'GOOS', 'GOARCH']},
          'go_version': subprocess.check_output(['go', 'version']).decode().strip(),
          'overlay_sha256': sha(overlay.read_bytes()), 'overlay_files': len(replace),
          'repository_inputs': len(before), 'all_inputs_equal_before_after': before == after,
          'before': before, 'after': after}
assert completed.returncode == 0, completed.stderr.decode()
assert before == after
result['binary_sha256'] = sha(binary.read_bytes())
result['binary_bytes'] = binary.stat().st_size
(OUT / 'host-pluginuninstall-reviewed-build-source-binding.json').write_text(json.dumps(result, indent=2) + '\n')
info = subprocess.run(['go', 'version', '-m', str(binary)], capture_output=True)
assert info.returncode == 0
(OUT / 'host-pluginuninstall-reviewed-buildinfo.txt').write_bytes(info.stdout)
print(json.dumps({k: result[k] for k in ['base_revision', 'frozen_PUI_manifest_sha256', 'exit_code', 'overlay_files', 'repository_inputs', 'binary_sha256', 'binary_bytes']}))
