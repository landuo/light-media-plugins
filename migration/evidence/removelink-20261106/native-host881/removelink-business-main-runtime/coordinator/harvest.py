from pathlib import Path, PurePosixPath
import datetime, hashlib, io, json, subprocess, tarfile

out = Path(__file__).resolve().parent / 'raw'
assert not (out/'harvest-manifest.json').exists(), 'preserve completed immutable harvest'
remote = r'''
from pathlib import Path
import io, os, sys, tarfile
assert os.getuid() == 1000
roots = {
 'SDK98': (Path('/home/admin/light-media-plugins-migration-sdk98-20261105'), 'light-media-plugins/SDK98/20261105/owned-only', []),
 'Rlk': (Path('/home/admin/light-media-plugins-migration-removelink-20261105'), 'light-media-plugins/RemoveLink/20261105/owned-only', ['business-main-1']),
}
files = []
for label, (root, marker, runs) in roots.items():
 assert root.is_dir() and not root.is_symlink()
 assert (root/'.task-owned').read_text().strip() == marker
 files.append((root/'.task-owned', label+'/.task-owned'))
 for run in runs:
  base = root/run
  assert (base/'.task-owned').is_file() and not base.is_symlink(), run
  wanted = [root/(run+'-command.json'), root/(run+'.log'), base/'.task-owned', base/'evidence/observations.jsonl']
  wanted += list((base/'evidence').glob('host-*.log'))
  wanted += list((base/'evidence').glob('browser-files-*.json'))
  for app in [base, base/'app']:
   if (app/'logs/app.jsonl').is_file(): wanted.append(app/'logs/app.jsonl')
   wanted += list((app/'logs/plugins').glob('*.log'))
  for f in sorted(set(wanted)):
   assert f.is_file() and not f.is_symlink(), f
   assert all(not p.is_symlink() for p in [f.parent, *list(f.parents)[:-1]])
   files.append((f, label+'/'+str(f.relative_to(root))))
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|') as t:
 for path, name in files:
  data = path.read_bytes(); item = tarfile.TarInfo(name)
  item.size = len(data); item.mode = 0o644; t.addfile(item, io.BytesIO(data))
'''
result = subprocess.run(['ssh', 'admin@192.168.8.129', 'python3', '-'], input=remote.encode(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
out.mkdir(exist_ok=True)
files = []
with tarfile.open(fileobj=io.BytesIO(result.stdout), mode='r:') as t:
 for item in t.getmembers():
  rel = PurePosixPath(item.name)
  assert not rel.is_absolute() and '..' not in rel.parts and item.isfile()
  data = t.extractfile(item).read(); dest = out.joinpath(*rel.parts)
  dest.parent.mkdir(parents=True, exist_ok=True)
  if dest.exists(): assert dest.read_bytes() == data, dest
  else: dest.write_bytes(data)
  files.append({'path': str(rel), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
runs = {}
for label, names in {'SDK98':[], 'Rlk':['business-main-1']}.items():
 for run in names:
  command = json.loads((out/label/(run+'-command.json')).read_text())
  observations = [json.loads(s) for s in (out/label/run/'evidence/observations.jsonl').read_text().splitlines() if s]
  app = out/label/run/'logs/app.jsonl'
  if not app.is_file(): app = out/label/run/'app/logs/app.jsonl'
  lines = app.read_text().splitlines()
  errors = [json.loads(s) for s in lines if s and json.loads(s).get('level','').upper() == 'ERROR']
  runs[run] = {'exit_code': command['exit_code'], 'seconds': command['seconds'], 'observations': len(observations), 'last_observation': observations[-1], 'module_declaration_failed': sum('module_declaration_failed' in s for s in lines), 'error_events': len(errors)}
manifest = {'classification':'allowlisted actual Rlk successful history/customscrap/trickplay/empty-child and actual owned notice receiver native ordinaryMain; no private database/key/routing ciphertext copied; excludes database, credentials, key, UI-ready, certificates, binaries and private configurations', 'collected_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'runs':runs, 'files':files}
(out/'harvest-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'runs':runs, 'files':len(files), 'manifest_sha256':hashlib.sha256((out/'harvest-manifest.json').read_bytes()).hexdigest()}, ensure_ascii=False, indent=2))
