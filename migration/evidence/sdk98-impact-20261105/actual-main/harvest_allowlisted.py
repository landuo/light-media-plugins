from pathlib import Path
import base64,hashlib,json,re,os
root=Path('/home/admin/light-media-plugins-migration-sdk98-20261105')
assert os.getuid()==1000
assert (root/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
allowed=[]
for n in [3,4]:
 allowed += [f'main-run-{n}-command.json',f'main-run-{n}.log']
 allowed += [f'main-run-{n}/evidence/observations.jsonl',f'main-run-{n}/evidence/host-1.log',f'main-run-{n}/evidence/host-2.log',f'main-run-{n}/logs/app.jsonl']
 allowed += [f'main-run-{n}/logs/plugins/{plugin}.log'for plugin in ['categoryeditor','torrenttransfer','torrenttransfermusic','sitestatistic']]
files=[];missing=[]
for name in allowed:
 p=root/name
 if not p.is_file():missing.append(name);continue
 assert not p.is_symlink() and p.resolve().is_relative_to(root.resolve())
 assert p.stat().st_size<32*1024*1024
 b=p.read_bytes()
 # These fields are removed by the actual HTTP recorder. Reject accidentally
 # unredacted structured secrets before any file content crosses SSH.
 assert not re.search(rb'(?i)"(?:password|api_token|authorization|cookie|apikey)"\s*:\s*"(?!\[redacted\])[^"\s]+',b),name
 files.append({'path':name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'base64':base64.b64encode(b).decode()})
print(json.dumps({'classification':'marker-verified explicit allowlist of owned sanitized observations/logs/commands only; no DB/key/config/CA/cookie files','remote_root':str(root),'files':files,'missing_optional_logs':missing}))
