from pathlib import Path
import subprocess,json,base64,hashlib
w=Path(__file__).resolve().parent
payload=r'''
from pathlib import Path
import os,hashlib,json,base64,re
r=Path('/home/admin/light-media-plugins-migration-pluginuninstall-20261105');assert os.getuid()==1000 and (r/'.task-owned').read_text()=='light-media-plugins/PluginUnInstall/20261105/owned-only'
names=['package-main-1.log','package-main-1-command.json','package-main-1/runtime/evidence/observations.jsonl','package-main-1/runtime/evidence/host-1.log','package-main-1/runtime/logs/app.jsonl']+[f'package-main-1/runtime/logs/plugins/{x}.log'for x in ['pluginuninstall','pluginuninstallpackage','ownedpuifixture']]
files=[];missing=[]
for name in names:
 p=r/name
 if not p.is_file():missing.append(name);continue
 assert not p.is_symlink() and p.resolve().is_relative_to(r.resolve())
 b=p.read_bytes();assert len(b)<32*1024*1024
 assert not re.search(rb'(?i)"(?:password|api_token|authorization|cookie|apikey)"\s*:\s*"(?!\[redacted\])[^"\s]+',b),name
 files.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'base64':base64.b64encode(b).decode()})
print(json.dumps({'classification':'canonical actual ordinary Main package smoke, exact marker-owned sanitized command/log/HTTP observations only; no DB/key/config/credentials','files':files,'missing_optional':missing}))
'''
p=subprocess.run(['ssh','admin@192.168.8.129','python3','-'],input=payload.encode(),capture_output=True);assert p.returncode==0,p.stderr.decode();v=json.loads(p.stdout);out=w/'package-main-harvest';out.mkdir(exist_ok=True)
for f in v['files']:
 b=base64.b64decode(f.pop('base64'));assert hashlib.sha256(b).hexdigest()==f['sha256'];q=out/f['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
(out/'manifest.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'files':len(v['files']),'manifest_sha256':hashlib.sha256((out/'manifest.json').read_bytes()).hexdigest()}))
