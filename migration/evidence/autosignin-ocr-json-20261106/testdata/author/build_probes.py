from pathlib import Path
import json,os,time,hashlib,subprocess
P=Path.cwd();w=Path(__file__).resolve().parent;inputs=set()
for n in ['new','old-parser','old-binding']:
 j=json.loads((w/('probe-'+n+'-overlay.json')).read_text())
 # The identical backend/frozen wrapper overlays were only needed before Root
 # integration; current true code now supplies them and keeps F1/F2.
 for k in list(j['Replace']):
  if k.endswith('/sdk_backend.go')or k.endswith('/internal/sdk/ocr_host.go'):del j['Replace'][k]
 (w/('probe-'+n+'-overlay.json')).write_text(json.dumps(j,indent=2)+'\n');inputs.update(Path(v)for v in j['Replace'].values())
inputs.update(Path(p)for p in subprocess.check_output(['rg','--files','plugins/autosignin','internal/sdk','cmd/auto-sign-in','-g','*.go'],text=True).splitlines());inputs.update(P/n for n in ['go.mod','go.sum']);snap=lambda:{str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest()for p in sorted(inputs)};before=snap();(w/'probe-inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');rows=[]
for n in ['new','old-parser','old-binding']:
 out=w/(n+'-domain-probe-linux');cmd=['go','build','-p=1','-trimpath','-buildvcs=false','-ldflags=-s -w','-mod=readonly','-modfile=work/migration-20261105/autosignin-implementation-20261106/autosignin.mod','-overlay='+str(w/('probe-'+n+'-overlay.json')),'-o',str(out),'./cmd/auto-sign-in'];start=time.monotonic();p=subprocess.run(cmd,cwd=P,capture_output=True,env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0','GOFLAGS':''});(w/(n+'-probe-build.stdout')).write_bytes(p.stdout);(w/(n+'-probe-build.stderr')).write_bytes(p.stderr);rows.append({'argv':cmd,'cwd':str(P),'env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0','GOFLAGS':''},'exit':p.returncode,'seconds':time.monotonic()-start,'sha256':hashlib.sha256(out.read_bytes()).hexdigest()if p.returncode==0 else None});(w/'probe-builds.json').write_text(json.dumps(rows,indent=2)+'\n');print(n,p.returncode,flush=True);assert p.returncode==0,p.stderr.decode()
after=snap();(w/'probe-inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');(w/'probe-stable.json').write_text(json.dumps({'count':len(before),'same':before==after},indent=2)+'\n');assert before==after
