BOM={'bin/host': {'sha256': '062da6f0e5f5814dc4f60ac8bb30c7240c2d71b940cc4250261cdf97bed136fb', 'bytes': 57200802}, 'bin/worker': {'sha256': '02ece64a7ecb85c64b126279014d026d5684591cd19237b24e12af8108481269', 'bytes': 12779682}, 'bin/cli': {'sha256': '72ee655a8aa706fa487201047bba360902886828d608f4efac31a40e0f8d5865', 'bytes': 25215138}, 'bin/driver': {'sha256': '7428de07d49465ed8177836ba98e3ce2bfd707c54a182f852ec6fd0135c8b86f', 'bytes': 9715874}}

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
