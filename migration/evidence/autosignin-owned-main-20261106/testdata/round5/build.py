from pathlib import Path
import json,subprocess,hashlib,time,os
P=Path.cwd();H=P.parent/'light-media';W=Path(__file__).resolve().parent;D=P/'work/autosignin-real-integration-20261106/autosignin_owned_site_main_test.go'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def inputs(root):
 names=subprocess.check_output(['git','ls-files','-z'],cwd=root).split(b'\0')
 return {str(root/os.fsdecode(n)):sha(root/os.fsdecode(n)) for n in names if n and (root/os.fsdecode(n)).is_file()}|{str(D):sha(D)}
env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0','GOFLAGS':'','GOPROXY':'off'}
rows=[]
for name,root,args in [('worker',P,['build','-p=1','-trimpath','-buildvcs=false','-ldflags=-s -w','-o',str(W/'worker'),'./cmd/auto-sign-in']),('host',H,['build','-p=1','-trimpath','-buildvcs=false','-ldflags=-s -w','-o',str(W/'host'),'./cmd/server']),('driver',P,['test','-p=1','-c','-ldflags=-s -w','-overlay='+str(W/'driver-overlay.json'),'-o',str(W/'driver'),'./tests/integration'])]:
 before=inputs(root);(W/(name+'-before.json')).write_text(json.dumps(before,indent=2)+'\n');t=time.monotonic();r=subprocess.run(['go']+args,cwd=root,env=env,capture_output=True);elapsed=time.monotonic()-t
 (W/(name+'.stdout')).write_bytes(r.stdout);(W/(name+'.stderr')).write_bytes(r.stderr);after=inputs(root);(W/(name+'-after.json')).write_text(json.dumps(after,indent=2)+'\n')
 row={'name':name,'argv':['go']+args,'cwd':str(root),'env':{k:env[k]for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOPROXY']},'exit':r.returncode,'seconds':elapsed,'inputs':len(before),'stable':before==after,'sha256':sha(W/name)if r.returncode==0 else None,'production_overlay':False};rows.append(row);(W/'builds.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(row),flush=True);assert r.returncode==0 and before==after
