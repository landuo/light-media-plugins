from pathlib import Path
import base64, hashlib, json, subprocess

OUT=Path(__file__).resolve().parent
REMOTE=r'''
from pathlib import Path
import base64,hashlib,json,os,re
assert os.getuid()==1000
roots=[('/home/admin/light-media-plugins-migration-pluginuninstall-20261105','light-media-plugins/PluginUnInstall/20261105/owned-only','pui',1,['PluginUnInstall','PluginUnInstallowned','OwnedPuiFixture','OwnedPuiFixtureui','MPServerStatus']),('/home/admin/light-media-plugins-migration-sdk98-20261105','light-media-plugins/SDK98/20261105/owned-only','impact',5,['categoryeditor','torrenttransfer','torrenttransfermusic','sitestatistic'])]
files=[];missing=[]
for root,marker,kind,n,plugins in roots:
 r=Path(root);assert (r/'.task-owned').read_text().strip()==marker
 stem=f'main-run-{n}'; runtime=stem+'/runtime' if kind=='pui' else stem
 names=[stem+'-command.json',stem+'.log',runtime+'/evidence/observations.jsonl',runtime+'/logs/app.jsonl']
 names += [runtime+f'/evidence/host-{i}.log' for i in range(1,20)]
 names += [runtime+'/logs/plugins/'+p.lower()+'.log' for p in plugins]
 for name in names:
  p=r/name
  if not p.is_file():missing.append(kind+'/'+name);continue
  assert not p.is_symlink() and p.resolve().is_relative_to(r.resolve())
  b=p.read_bytes();assert len(b)<32*1024*1024
  assert not re.search(rb'(?i)"(?:password|api_token|authorization|cookie|apikey)"\s*:\s*"(?!\[redacted\])[^"\s]+',b),name
  files.append({'path':kind+'/'+name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'base64':base64.b64encode(b).decode()})
print(json.dumps({'classification':'actual Linux native Main completed; marker-bound explicit allowlist of sanitized commands/logs/observations only; no DB/key/config/UI-ready/credentials','files':files,'missing_optional_logs':missing}))
'''
p=subprocess.run(['ssh','admin@192.168.8.129','python3','-'],input=REMOTE.encode(),capture_output=True)
assert p.returncode==0,p.stderr.decode()
data=json.loads(p.stdout);dest=OUT/'actual-harvest';dest.mkdir(exist_ok=True)
for f in data['files']:
 b=base64.b64decode(f.pop('base64'));assert hashlib.sha256(b).hexdigest()==f['sha256']
 d=dest/f['path'];d.parent.mkdir(parents=True,exist_ok=True)
 if d.exists():assert d.read_bytes()==b
 d.write_bytes(b)
(dest/'manifest.json').write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({'files':len(data['files']),'manifest_sha256':hashlib.sha256((dest/'manifest.json').read_bytes()).hexdigest(),'roots':[str(dest/'pui'),str(dest/'impact')]}))
