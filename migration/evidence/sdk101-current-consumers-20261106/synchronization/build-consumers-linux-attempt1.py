from pathlib import Path
import json,hashlib,os,subprocess,time
r=Path.cwd();w=Path(__file__).resolve().parent;out=w/'bins';out.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();origin=r/'SDK_ORIGIN.json';assert sha(origin)=='b417c613195590062759633af4142f8a433c8d2fc8279fb36fa00e33e4d112a0';old=json.load(open(w/'consumer-inputs-after.json'));assert all(sha(r/p)==h for p,h in old.items());(w/'linux-consumer-inputs-before.json').write_text(json.dumps(old,indent=2)+'\n');env=dict(os.environ,GOOS='linux',GOARCH='amd64',CGO_ENABLED='0',GOFLAGS='',GOPROXY='off');rows=[]
registry=json.load(open('build-plugins.json'))['plugins'];builds=[(row['id'],row['package'],None)for row in registry]
for ident,pkg,virtual,version,nextversion in [('RemoveLink-update','./cmd/remove-link','plugins/removelink/manifest.go','2.18','2.18.1'),('PluginUnInstall-update','./cmd/plugin-uninstall','plugins/pluginuninstall/plugin.go','2.2','2.2.1')]:
 p=r/virtual;text=p.read_text();a='Version: "'+version+'"';b='Version: "'+nextversion+'"';assert text.count(a)==1;p2=w/(ident+'-version-only.go.txt');p2.write_text(text.replace(a,b));overlay=w/(ident+'-overlay.json');overlay.write_text(json.dumps({'Replace':{str(p):str(p2)}},indent=2)+'\n');builds.append((ident,pkg,overlay))
for ident,pkg,overlay in builds:
 space=os.statvfs(r);free=space.f_bavail*space.f_frsize
 if free<320*1024**2:raise RuntimeError('owned disk headroom below320MiB; no more build before resource coordination')
 path=out/(ident+'-linux');assert not path.exists();cmd=['go','build','-p=1','-trimpath','-buildvcs=false',*(['-overlay='+str(overlay)]if overlay else[]),'-o',str(path),pkg];start=time.monotonic();p=subprocess.run(cmd,env=env,cwd=r,capture_output=True);(w/(ident+'-linux-build.stdout')).write_bytes(p.stdout);(w/(ident+'-linux-build.stderr')).write_bytes(p.stderr);row={'id':ident,'command':cmd,'environment':{k:env[k]for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOPROXY']},'source_origin_sha256':sha(origin),'exit':p.returncode,'seconds':time.monotonic()-start,'free_bytes_before':free,'classification':'new101consumer compile only; actualnativeMain/current7impact pending'}
 if p.returncode==0:
  row.update(artifact=str(path),sha256=sha(path),bytes=path.stat().st_size);v=subprocess.run(['go','version','-m',str(path)],capture_output=True,check=True);(w/(ident+'-linux-buildinfo.txt')).write_bytes(v.stdout)
 rows.append(row);(w/'linux-consumer-builds.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:row[k]for k in ['id','exit','seconds','sha256','bytes']if k in row}),flush=True)
 if p.returncode:raise SystemExit(p.returncode)
assert sha(origin)=='b417c613195590062759633af4142f8a433c8d2fc8279fb36fa00e33e4d112a0';assert all(sha(r/p)==h for p,h in old.items());(w/'linux-consumer-inputs-after.json').write_text(json.dumps(old,indent=2)+'\n');print(json.dumps({'stable_inputs':len(old),'built':len(rows)}))
