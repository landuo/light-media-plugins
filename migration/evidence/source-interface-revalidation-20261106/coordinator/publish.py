from pathlib import Path
import hashlib, json

root = Path.cwd()
out = root/'migration/evidence/source-interface-revalidation-20261106'
copies = []; omitted = []
sha = lambda data: hashlib.sha256(data).hexdigest()

def put(src, rel, expected=None):
 src = Path(src); data = src.read_bytes()
 assert not src.is_symlink() and len(data) < 20*1024*1024, src
 assert data[:4] not in [b'\x7fELF', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf'], src
 assert not any(s in src.name.lower() for s in ['ui-ready','secret.key','light-media.db','private']), src
 if expected: assert sha(data) == expected, src
 dest = out/rel; dest.parent.mkdir(parents=True, exist_ok=True)
 if dest.exists(): assert dest.read_bytes() == data, dest
 else: dest.write_bytes(data)
 copies.append({'source':str(src), 'public':str(dest.relative_to(root)), 'sha256':sha(data), 'bytes':len(data)})

for name in ['source-module-manifest','source-auth-declaration-addon']:
 base = root/'work/migration-20261106'/name
 safe = json.loads((base/'safe-copy.json').read_text())
 for f in safe['files']:
  src = Path(f['path']); put(src, 'producer/'+name+'/'+str(src.relative_to(base)), f['sha256'])
 for p in [base/'freeze.json', base/'safe-copy.json']:
  if not any(x['source'] == str(p) for x in copies): put(p, 'producer/'+name+'/'+p.name)

for name in ['manifest-methods-review','auth-declaration-addon']:
 base = root/'work/sites-review-20261106'/name
 for f in json.loads((base/'artifact-manifest.json').read_text()):
  if f.get('public_copy', True): put(base/f['path'], 'independent/'+name+'/'+f['path'], f['sha256'])
  else:
   assert sha((base/f['path']).read_bytes()) == f['sha256']
   omitted.append({'source':str(base/f['path']), 'sha256':f['sha256'], 'reason':'private host recording source, not a plugin runtime dependency'})
 for name2 in ['artifact-manifest.json','review-evidence.json']:
  put(base/name2, 'independent/'+name+'/'+name2)

for name in ['pui-current-driver','pui-current-declarations-main-preparation']:
 base = root/'work/migration-20261106'/name
 for p in sorted(base.iterdir()):
  if p.is_file() and p.read_bytes()[:4] != b'\x7fELF': put(p, 'driver/'+name+'/'+p.name)

for name in ['actual-harvest']:
 base = root/'work/migration-20261106/current-consumer-main'/name
 for p in sorted(base.rglob('*')):
  if p.is_file(): put(p, 'old20-and-PUI3/'+str(p.relative_to(base)))
base = root/'work/migration-20261106/current23-actual-harvest/raw'
for p in sorted(base.rglob('*')):
 if p.is_file(): put(p, 'current23-Main/'+str(p.relative_to(base)))

base = root/'work/migration-20261106/current-consumer-main'
for name in ['run_four.py','run_four_auth.py','run_pui3.py','four-auth-inputs.json','pui3-inputs.json']:
 put(base/name, 'coordinator/'+name)
for name in ['harvest.py','publish.py']:
 put(Path(__file__).parent/name, 'coordinator/'+name)

base = Path('/Users/accidia/projects/light-media/work/shared-host-getter-gates-20261106')
for name in ['build.py','build-source-binding.json','build.log','buildinfo.txt']:
 put(base/name, 'host-build/'+name)

manifest = {'classification':'exact-byte finite source-method, Auth correction, real-worker/App, native ordinary-Main and executable-input observations. Historical20 reports are retained and corrected by current23 Auth addon; no whole migration claim.', 'host_dependency':'landuo/light-media@651dd2c3f75f4be74951d0a552f93a9079046e1d; host finite source/getter/state/query evidence lives in that repository', 'files':copies, 'private_source_inputs_not_copied':omitted}
(out/'copy-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps({'files':len(copies), 'bytes':sum(f['bytes'] for f in copies), 'omitted':len(omitted), 'copy_manifest_sha256':sha((out/'copy-manifest.json').read_bytes())}))
