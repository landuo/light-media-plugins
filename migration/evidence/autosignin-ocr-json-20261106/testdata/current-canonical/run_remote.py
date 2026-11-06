from pathlib import Path
import subprocess,json,hashlib,tarfile,io,shlex,time
w=Path(__file__).resolve().parent;old=w.parent/'source-ocr-value-domain-20261106'
root='/home/admin/light-media-plugins-source-ocr-json-integrated-20261106';marker='light-media-plugins/source-ocr-json-integrated/20261106/owned-only'
files={'bin/current-domain-app-linux.test':w/'current-domain-app-linux.test','bin/current-domain-probe-linux':w/'current-domain-probe-linux',**{'oracles/'+n:old/n for n in ['source.stdout','depth-source.stdout','empty-depth-source.stdout','hdsky-source.stdout']}}
owned=b'source OCR integrated actual SDK gate\n'
bom={n:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}for n,p in files.items()};bom['internal/app/.owned']={'sha256':hashlib.sha256(owned).hexdigest(),'bytes':len(owned)}
(w/'bundle-bom.json').write_text(json.dumps(bom,indent=2)+'\n')
setup=f'''from pathlib import Path
r=Path({root!r});m={marker!r}
assert not r.exists(), 'new owned root already exists; inspect before reuse'
r.mkdir(mode=0o700);(r/'.task-owned').write_text(m+'\\n');(r/'bundle').mkdir(mode=0o700)
'''
r=subprocess.run(['ssh','admin@192.168.8.129','python3 -'],input=setup.encode(),capture_output=True);(w/'remote-setup.stdout').write_bytes(r.stdout);(w/'remote-setup.stderr').write_bytes(r.stderr);assert r.returncode==0,r.stderr.decode()
cmd=['ssh','admin@192.168.8.129','tar -x -f - -C '+shlex.quote(root+'/bundle')];up=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with tarfile.open(fileobj=up.stdin,mode='w|')as tar:
 for n,p in sorted(files.items()):tar.add(p,arcname=n,recursive=False)
 entry=tarfile.TarInfo('internal/app/.owned');entry.size=len(owned);entry.mode=0o444;tar.addfile(entry,io.BytesIO(owned))
up.stdin.close();out=up.stdout.read();err=up.stderr.read();code=up.wait();(w/'upload.stdout').write_bytes(out);(w/'upload.stderr').write_bytes(err);assert code==0,err.decode()
runner=(old/'remote-runner.py').read_text()
changes=[('/home/admin/light-media-plugins-source-ocr-value-domain-20261106',root),('light-media-plugins/source-ocr-value-domain/20261106/owned-only',marker),("run=r/'run-r2'","run=r/'run-r1'"),("for phase,probe in [('old-parser','old-parser'),('old-binding','old-binding'),('new','new')]:","for phase,probe in [('current','current')]:"),('lm-source-ocr-domain-r2-','lm-source-ocr-json-integrated-'),('/owned/bin/domain-app-linux.test','/owned/bin/current-domain-app-linux.test'),('task=lm-source-ocr-value-domain-20261106','task=lm-source-ocr-json-integrated-20261106'),("assert rows[0]['exit_code']!=0 and rows[1]['exit_code']!=0 and rows[2]['exit_code']==0,'old/new or native semantic gate failed'","assert len(rows)==1 and rows[0]['exit_code']==0 and rows[0]['counts']['pass_nodes']==75,'integrated true-production gate failed'")]
for before,after in changes:assert before in runner,before;runner=runner.replace(before,after)
lines=runner.splitlines()
for i,line in enumerate(lines):
 if ';bom='in line:
  lines[i]=line.split(';bom=',1)[0]+';bom='+repr(bom);break
else:raise AssertionError('no BOM')
runner='\n'.join(lines)+'\n';compile(runner,'remote-runner','exec');(w/'remote-runner.py').write_text(runner)
(w/'runner-refinement.json').write_text(json.dumps({'frozen_runner':str(old/'remote-runner.py'),'frozen_sha256':hashlib.sha256((old/'remote-runner.py').read_bytes()).hexdigest(),'changes':changes,'bom_replaced':True,'test_and_oracles_unchanged':True,'new_source_runs':0},indent=2)+'\n')
start=time.monotonic();r=subprocess.run(['ssh','admin@192.168.8.129','python3 -'],input=runner.encode(),capture_output=True);(w/'remote-run.stdout').write_bytes(r.stdout);(w/'remote-run.stderr').write_bytes(r.stderr);(w/'remote-command.json').write_text(json.dumps({'argv':['ssh','admin@192.168.8.129','python3 -'],'stdin_sha256':hashlib.sha256(runner.encode()).hexdigest(),'exit':r.returncode,'seconds':time.monotonic()-start},indent=2)+'\n');print(r.stdout.decode());print(r.stderr.decode());print('remote_exit',r.returncode,flush=True)
x=subprocess.run(['ssh','admin@192.168.8.129','tar -c -f - -C '+shlex.quote(root)+' run-r1'],capture_output=True);assert x.returncode==0,x.stderr.decode()
with tarfile.open(fileobj=io.BytesIO(x.stdout),mode='r:')as tar:
 for m in tar.getmembers():assert not m.issym()and not m.islnk()and(w/m.name).resolve().is_relative_to(w.resolve())
 tar.extractall(w,filter='data')
raise SystemExit(r.returncode)
