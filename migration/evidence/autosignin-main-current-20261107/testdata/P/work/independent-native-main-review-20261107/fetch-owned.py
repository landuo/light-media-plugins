from pathlib import Path
import json,subprocess,hashlib,base64,time
w=Path(__file__).resolve().parent;a=w.parent/'autosignin-native-main-20261107';bom=json.loads((a/'bundle-bom.json').read_text());root='/home/admin/light-media-plugins-root-asi-native-20261107';marker='light-media-plugins/root-asi-native/20261107/owned-only'
script='ROOT='+repr(root)+'\nMARKER='+repr(marker)+'\nBOM='+repr(bom)+'\n'+r'''
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
'''
(w/'fetch-script.py').write_text(script);argv=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','admin@192.168.8.129','python3 -'];t=time.monotonic();r=subprocess.run(argv,input=script.encode(),capture_output=True,timeout=30);(w/'fetch.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode();j=json.loads(r.stdout);dest=w/'raw';dest.mkdir()
for v in j['files']:
 p=dest/v['path'];p.parent.mkdir(parents=True,exist_ok=True);b=base64.b64decode(v.pop('data'));assert len(b)==v['bytes']and hashlib.sha256(b).hexdigest()==v['sha256'];p.write_bytes(b)
(w/'fetch-evidence.json').write_text(json.dumps(j,indent=2)+'\n');(w/'fetch-command.json').write_text(json.dumps(dict(argv=argv,stdin_sha256=hashlib.sha256(script.encode()).hexdigest(),exit=r.returncode,seconds=time.monotonic()-t),indent=2)+'\n');print(json.dumps(dict(files=[{'path':v['path'],'bytes':v['bytes']}for v in j['files']],scope=j['read_scope'])))
