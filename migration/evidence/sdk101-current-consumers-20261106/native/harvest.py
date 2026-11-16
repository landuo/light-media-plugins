from pathlib import Path
import base64,json,subprocess,hashlib,re
out=Path(__file__).resolve().parent
script=r'''
from pathlib import Path
import base64,json,hashlib,os
r=Path('/home/admin/light-media-plugins-migration-sdk98-20261105/sdk101-current-consumers-1');assert os.getuid()==1000 and(r/'.task-owned').read_text().strip()=='light-media-plugins/sdk101-current-consumers/20261106/owned-only'
rows=[]
for p in sorted(r.rglob('*')):
 if not p.is_file() or p.is_symlink():continue
 name=str(p.relative_to(r));admit=p.parent==r and p.suffix in ['.json','.log'] or '/evidence/'in str(p) and (p.name=='observations.jsonl' or p.name.startswith('host-')and p.suffix=='.log')
 if not admit:continue
 b=p.read_bytes();assert len(b)<2000000
 rows.append({'path':name,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'data':base64.b64encode(b).decode()})
print(json.dumps(rows))
'''
p=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=script.encode(),capture_output=True);(out/'harvest.stderr').write_bytes(p.stderr);assert p.returncode==0
rows=json.loads(p.stdout);manifest=[]
for row in rows:
 b=base64.b64decode(row.pop('data'));assert hashlib.sha256(b).hexdigest()==row['sha256'];assert not re.search(rb'(?i)"(?:password|api_token|authorization|cookie|apikey)"\s*:\s*"(?!\[redacted\])[^"\s]+',b),row['path']
 q=out/'actual-harvest'/row['path'];q.parent.mkdir(parents=True,exist_ok=True);assert not q.exists();q.write_bytes(b);manifest.append(row)
(out/'harvest-manifest.json').write_text(json.dumps({'classification':'explicit allowlist commands,driverlogs and sanitized observations/hostlogs only; no private DB/key/config/UI-ready/wire credentials','remote_root':'/home/admin/light-media-plugins-migration-sdk98-20261105/sdk101-current-consumers-1','files':manifest},indent=2)+'\n')
print(json.dumps({'files':len(manifest),'bytes':sum(x['bytes']for x in manifest)}))
