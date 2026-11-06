from pathlib import Path
import json,subprocess,hashlib,tarfile,io,time
P=Path.cwd();w=Path(__file__).resolve().parent;root='/home/admin/light-media-plugins-root-asi-owned-20261106-r4';marker='light-media-plugins/root-asi-owned/20261106/owned-only';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={'bin/host-main-linux':w/'host','bin/auto-sign-in-linux':w/'worker','bin/main-driver-linux.test':w/'driver','source/form.json':P/'plugins/autosignin/form.json','source/api-oracle.json':P/'work/notice-api-20261106/source.stdout'}
bom={n:{'sha256':sha(p),'bytes':p.stat().st_size}for n,p in files.items()};(w/'empty-main-bundle.json').write_text(json.dumps(bom,indent=2)+'\n')
setup='''from pathlib import Path
r=Path(%r);assert not r.exists();r.mkdir(mode=0o700);(r/'.task-owned').write_text(%r+'\\n');(r/'bundle').mkdir(mode=0o700);(r/'tmp').mkdir(mode=0o700)
'''%(root,marker)
r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=setup.encode(),capture_output=True);(w/'empty-main-setup.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
p=subprocess.Popen(['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-xf','-','-C',root+'/bundle'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with tarfile.open(fileobj=p.stdin,mode='w|')as tar:
    for n,f in files.items():tar.add(f,arcname=n,recursive=False)
p.stdin.close();out=p.stdout.read();err=p.stderr.read();code=p.wait();(w/'empty-main-upload.stderr').write_bytes(err);assert code==0,err.decode()
script='''from pathlib import Path
import subprocess,json,hashlib,os,time
r=Path(ROOT);b=r/'bundle';bom=BOM
assert os.getuid()==1000 and not r.is_symlink()and(r/'.task-owned').read_text().strip()==MARKER
for n,v in bom.items():
 p=b/n;assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(b.resolve())and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'];p.chmod(0o755 if n.startswith('bin/')else 0o444)
env={**os.environ,'TMPDIR':str(r/'tmp'),'CATEGORYEDITOR_HOST_BINARY':str(b/'bin/host-main-linux'),'CATEGORYEDITOR_RUNTIME_DIR':str(r/'runtime'),'AUTOSIGNIN_WORKER_BINARY':str(b/'bin/auto-sign-in-linux'),'AUTOSIGNIN_FORM_SOURCE':str(b/'source/form.json'),'AUTOSIGNIN_API_SOURCE':str(b/'source/api-oracle.json')};args=[str(b/'bin/main-driver-linux.test'),'-test.v','-test.timeout=3m','-test.run=^TestAutoSignInActualMainOwnedSiteOnceAndClone$'];t=time.monotonic();p=subprocess.run(args,cwd=r,env=env,capture_output=True,timeout=195);(r/'actual-main.stdout').write_bytes(p.stdout);(r/'actual-main.stderr').write_bytes(p.stderr);(r/'command.json').write_text(json.dumps({'argv':args,'exit':p.returncode,'seconds':time.monotonic()-t,'env':{k:env[k]for k in ['TMPDIR','CATEGORYEDITOR_HOST_BINARY','CATEGORYEDITOR_RUNTIME_DIR','AUTOSIGNIN_WORKER_BINARY','AUTOSIGNIN_FORM_SOURCE','AUTOSIGNIN_API_SOURCE']},'scope':'nativeordinaryGo cmd/server+standaloneproductionworker; ownedNexusprotocolpeer/real3-secondonce/physicalrequest/history/clone/cold/no-replay; no realPT/OCR/UI acceptance','network':'nativeownedloopback HTTP repository/Main, notnetnone; production services/configunmodified'},indent=2)+'\\n')
print(json.dumps({'exit':p.returncode,'seconds':time.monotonic()-t}));assert p.returncode==0
'''.replace('ROOT',repr(root)).replace('BOM',repr(bom)).replace('MARKER',repr(marker))
(w/'empty-main-remote-runner.py').write_text(script);t=time.monotonic();p=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=script.encode(),capture_output=True,timeout=220);(w/'empty-main-remote.stdout').write_bytes(p.stdout);(w/'empty-main-remote.stderr').write_bytes(p.stderr);(w/'empty-main-remote-command.json').write_text(json.dumps({'exit':p.returncode,'seconds':time.monotonic()-t,'script_sha256':sha(w/'empty-main-remote-runner.py')},indent=2)+'\n')
# Only sanitized test driver outputs are harvested. Runtime databases/auth keys
# and source-private configuration stay in the owned NAS directory until cleanup.
args=['ssh','-o','BatchMode=yes','admin@192.168.8.129','tar','-cf','-','-C',root,'actual-main.stdout','actual-main.stderr','command.json','runtime/evidence'];r=subprocess.run(args,capture_output=True);assert r.returncode==0,r.stderr.decode();dest=w/'empty-main-actual';dest.mkdir(exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(r.stdout))as tar:
    for x in tar.getmembers():assert not x.issym()and not x.islnk()and not Path(x.name).is_absolute()and'..'not in Path(x.name).parts
    tar.extractall(dest,filter='data')
print(p.stdout.decode());assert p.returncode==0,p.stderr.decode()
