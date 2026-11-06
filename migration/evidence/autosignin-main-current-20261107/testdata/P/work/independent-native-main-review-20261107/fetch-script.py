ROOT='/home/admin/light-media-plugins-root-asi-native-20261107'
MARKER='light-media-plugins/root-asi-native/20261107/owned-only'
BOM={'bin/host': {'sha256': '062da6f0e5f5814dc4f60ac8bb30c7240c2d71b940cc4250261cdf97bed136fb', 'bytes': 57200802}, 'bin/worker': {'sha256': '02ece64a7ecb85c64b126279014d026d5684591cd19237b24e12af8108481269', 'bytes': 12779682}, 'bin/cli': {'sha256': '72ee655a8aa706fa487201047bba360902886828d608f4efac31a40e0f8d5865', 'bytes': 25215138}, 'bin/driver': {'sha256': '97e544e53901c666d9654e237cd09079ac5040a2918bfa46f90ca37610e030ef', 'bytes': 9707682}}

from pathlib import Path
import hashlib,json,base64,subprocess,os
r=Path(ROOT);assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==MARKER and(r/'owned/.task-owned').read_text()==MARKER
bundles=[]
for n,v in BOM.items():
 p=r/'bundle'/n;assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to((r/'bundle').resolve());b=p.read_bytes();assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];bundles.append(dict(path=str(p),**v))
allowed=[r/'actual.stdout',r/'actual.stderr'];d=r/'owned/runtime/evidence';assert d.is_dir()and not d.is_symlink()and d.resolve().is_relative_to((r/'owned').resolve())
allowed+=sorted(p for p in d.rglob('*')if p.is_file())
files=[]
for p in allowed:
 assert not p.is_symlink()and p.resolve().is_relative_to(r.resolve());b=p.read_bytes();assert len(b)<20000000;files.append(dict(path=str(p.relative_to(r)),bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),data=base64.b64encode(b).decode()))
ps=subprocess.run(['docker','ps','-aq','--filter','name=^/lm-root-asi-native-20261107$'],capture_output=True,text=True);assert ps.returncode==0 and not ps.stdout.strip()
print(json.dumps(dict(root=ROOT,marker_exact=True,bundle=bundles,files=files,owned_container_ids=ps.stdout,read_scope='only exact owned marker/bundle BOM; actual.stdout/stderr and owned/runtime/evidence contents; no runtime DB/key/config or old service reads')))
