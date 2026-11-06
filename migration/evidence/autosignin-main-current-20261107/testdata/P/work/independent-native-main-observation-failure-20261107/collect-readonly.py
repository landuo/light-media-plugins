from pathlib import Path
import subprocess,json,hashlib,time,base64
w=Path(__file__).resolve().parent;a=w.parent/'autosignin-native-main-20261107';bom=json.loads((a/'bundle-bom.json').read_text());payload='BOM='+repr(bom)+'\n'+r'''
from pathlib import Path
import subprocess,json,datetime,time,hashlib,base64,os
root=Path('/home/admin/light-media-plugins-root-asi-native-20261107');assert os.getuid()==1000 and not root.is_symlink()and(root/'.task-owned').read_text()=='light-media-plugins/root-asi-native/20261107/owned-only'
assert(root/'owned-r2/.task-owned').read_text()=='light-media-plugins/root-asi-native/20261107/owned-only'
for n,v in BOM.items():
 f=root/'bundle'/n;assert f.is_file()and not f.is_symlink()and hashlib.sha256(f.read_bytes()).hexdigest()==v['sha256']and f.stat().st_size==v['bytes']
name='lm-root-asi-native-20261107';now=time.time();mtime=(root/'attempt3/command.json').stat().st_mtime
commands=[['docker','ps','-a','--no-trunc','--filter','name=^/'+name+'$'],['docker','inspect',name],['docker','container','inspect',name]]
# A fixed finite historical window around this task's command record, filtered
# to its exact task label. No unfiltered service/container listing is read.
start=max(0,int(mtime)-80);end=min(int(now),int(mtime)+80)
commands.append(['docker','events','--since',str(start),'--until',str(end),'--filter','type=container','--filter','label=task=lm-root-asi-native-20261107','--format','{{json .}}'])
results=[]
for argv in commands:
 b=time.monotonic()
 try:
  r=subprocess.run(argv,capture_output=True,timeout=15);results.append(dict(argv=argv,exit=r.returncode,seconds=time.monotonic()-b,stdout=r.stdout.decode(),stderr=r.stderr.decode()))
 except subprocess.TimeoutExpired as e:results.append(dict(argv=argv,exception='TimeoutExpired',stdout=(e.stdout or b'').decode(),stderr=(e.stderr or b'').decode()))
paths=[root/'attempt3/actual.stdout',root/'attempt3/actual.stderr',root/'attempt3/command.json'];d=root/'owned-r2/runtime/evidence';assert d.is_dir()and not d.is_symlink();paths+=sorted(x for x in d.rglob('*')if x.is_file())
files=[]
for f in paths:
 assert not f.is_symlink()and f.resolve().is_relative_to(root.resolve());b=f.read_bytes();assert len(b)<20000000;files.append(dict(path=str(f.relative_to(root)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),mtime_ns=f.stat().st_mtime_ns,data=base64.b64encode(b).decode()))
print(json.dumps(dict(now_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command_mtime_utc=datetime.datetime.fromtimestamp(mtime,datetime.timezone.utc).isoformat(),event_window_epoch=[start,end],bom_verified=True,commands=results,files=files,scope='read-only exact task marker/BOM/container metadata and bounded exact-label events; only own attempt3 stdout/stderr/record and owned-r2 runtime evidence, no DB/key/config or old service read')))
'''
(w/'collector.py').write_text(payload);argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','admin@192.168.8.129','python3 -'];b=time.monotonic();r=subprocess.run(argv,input=payload.encode(),capture_output=True,timeout=70);(w/'collector.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode();j=json.loads(r.stdout);d=w/'raw';d.mkdir()
for v in j['files']:
 f=d/v['path'];f.parent.mkdir(parents=True,exist_ok=True);data=base64.b64decode(v.pop('data'));assert hashlib.sha256(data).hexdigest()==v['sha256'];f.write_bytes(data)
(w/'readback.json').write_text(json.dumps(j,indent=2)+'\n');(w/'collector-command.json').write_text(json.dumps(dict(argv=argv,exit=r.returncode,seconds=time.monotonic()-b,stdin_sha256=hashlib.sha256(payload.encode()).hexdigest()),indent=2)+'\n');print(json.dumps(dict(commands=[{'argv':x['argv'],'exit':x.get('exit'),'stdout_bytes':len(x['stdout']),'stderr':x['stderr']}for x in j['commands']],files=[{'path':x['path'],'bytes':x['bytes']}for x in j['files']],window=j['event_window_epoch'])))
