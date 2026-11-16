from pathlib import Path
import subprocess,json,hashlib,tarfile,io,shlex
w=Path(__file__).resolve().parent;H=Path('/Users/accidia/projects/light-media');b=w/'bundle';b.mkdir(exist_ok=True)
files={**{'bin/'+n:w/n for n in ['domain-app-linux.test','new-domain-probe-linux','old-parser-domain-probe-linux','old-binding-domain-probe-linux']},**{'oracles/'+n:w/n for n in ['source.stdout','depth-source.stdout','empty-depth-source.stdout','hdsky-source.stdout']}}
for n,p in files.items():
 q=b/n;q.parent.mkdir(parents=True,exist_ok=True)
 if q.exists():
  assert q.is_file()and not q.is_symlink()and q.resolve().is_relative_to(b.resolve())
  q.chmod(0o600)
 q.write_bytes(p.read_bytes());q.chmod(0o755 if n.startswith('bin/')else 0o444)
(b/'internal/app').mkdir(parents=True,exist_ok=True);(b/'internal/app/.owned').write_text('source OCR owned actual standard SDK gate\n')
bom={str(p.relative_to(b)):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}for p in sorted(b.rglob('*'))if p.is_file()};(w/'bundle-bom.json').write_text(json.dumps(bom,indent=2)+'\n')
root='/home/admin/light-media-plugins-source-ocr-value-domain-20261106';marker='light-media-plugins/source-ocr-value-domain/20261106/owned-only'
setup=f'''from pathlib import Path
r=Path({root!r});m={marker!r}
if r.exists():assert not r.is_symlink()and(r/'.task-owned').read_text().strip()==m
else:r.mkdir(mode=0o700);(r/'.task-owned').write_text(m+'\\n')
(r/'bundle').mkdir(mode=0o700,exist_ok=True)
assert not(r/'bundle').is_symlink()
''';p=subprocess.run(['ssh','admin@192.168.8.129','python3 -'],input=setup.encode(),capture_output=True);(w/'remote-setup.stdout').write_bytes(p.stdout);(w/'remote-setup.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode()
a=['ssh','admin@192.168.8.129','tar -x --unlink-first -f - -C '+shlex.quote(root+'/bundle')];p=subprocess.Popen(a,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
with tarfile.open(fileobj=p.stdin,mode='w|')as tar:
 for n in sorted(bom):tar.add(b/n,arcname=n,recursive=False)
p.stdin.close();out=p.stdout.read();err=p.stderr.read();code=p.wait();(w/'upload.stdout').write_bytes(out);(w/'upload.stderr').write_bytes(err);assert code==0,err.decode()
runner=r'''from pathlib import Path
import json,hashlib,subprocess,time,re
r=Path(__ROOT__);assert not r.is_symlink()and(r/'.task-owned').read_text().strip()==__MARKER__;b=r/'bundle';assert not b.is_symlink();bom=__BOM__
for n,v in bom.items():
 p=b/n;assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(b.resolve())and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256'];p.chmod(0o755 if n.startswith('bin/')else 0o444)
run=r/'run-r1';run.mkdir(mode=0o700,exist_ok=False);rows=[]
for phase,probe in [('old-parser','old-parser'),('old-binding','old-binding'),('new','new')]:
 name='lm-source-ocr-domain-'+phase+'-20261106';cid=run/(phase+'.cid');pattern='^TestSourceOCRJSONDomainActualSDKWire$'
 script='mkdir -p /config/tmp\n/owned/bin/domain-app-linux.test -test.v -test.timeout=6m -test.run='+pattern+'\nowned_domain_exit=$?\nif test -f /tmp/observations.json; then\n printf "\\nOCR_DOMAIN_OBSERVATIONS_BEGIN\\n"\n cat /tmp/observations.json\n printf "\\nOCR_DOMAIN_OBSERVATIONS_END\\n"\nfi\nexit "$owned_domain_exit"'
 cmd=['docker','run','--no-healthcheck','--name',name,'--cidfile',str(cid),'--network','none','--read-only','--tmpfs','/tmp:rw,exec,nosuid,nodev,uid=1000,gid=1000,mode=0700','--tmpfs','/config:rw,exec,nosuid,nodev,uid=1000,gid=1000,mode=0700','--cap-drop','ALL','--security-opt','no-new-privileges','--user','1000:1000','--label','task=lm-source-ocr-value-domain-20261106','--mount','type=bind,src='+str(b)+',dst=/owned,readonly','--workdir','/owned/internal/app','--env','TMPDIR=/config/tmp','--env','OCR_DOMAIN_NETWORK_NONE=1','--env','OCR_DOMAIN_EVIDENCE_DIR=/owned/oracles','--env','OCR_DOMAIN_FIXTURE_BINARY=/owned/bin/'+probe+'-domain-probe-linux','--env','OCR_DOMAIN_OUTPUT=/tmp/observations.json','--entrypoint','/bin/sh','sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881','-c',script]
 start=time.monotonic();inspected=False
 try:
  with(run/(phase+'.stdout')).open('wb')as out,(run/(phase+'.stderr')).open('wb')as err:
   p=subprocess.Popen(cmd,stdout=out,stderr=err);got=None
   for attempt in range(200):
    if cid.exists()and cid.read_text().strip():
     got=subprocess.run(['docker','inspect',cid.read_text().strip()],capture_output=True)
     if got.returncode==0:break
    time.sleep(.03)
   assert got is not None and got.returncode==0,'inspect unavailable';d=json.loads(got.stdout)[0];f=dict(container_id=d['Id'],network=d['HostConfig']['NetworkMode'],readonly=d['HostConfig']['ReadonlyRootfs'],capdrop=d['HostConfig']['CapDrop'],security=d['HostConfig']['SecurityOpt'],user=d['Config']['User'],entrypoint=d['Config']['Entrypoint'],healthcheck=d['Config'].get('Healthcheck'),privileged=d['HostConfig']['Privileged'],mounts=[dict(Type=v['Type'],Source=v['Source'],Destination=v['Destination'],RW=v['RW'])for v in d['Mounts']],tmpfs=d['HostConfig']['Tmpfs']);(run/(phase+'-isolation.json')).write_text(json.dumps(f,indent=2)+'\n');assert f['network']=='none'and f['readonly']and f['user']=='1000:1000'and not f['privileged']and f['capdrop']==['ALL']and f['mounts']==[dict(Type='bind',Source=str(b),Destination='/owned',RW=False)]and set(f['tmpfs'])=={'/tmp','/config'}and f['healthcheck']['Test']==['NONE'];inspected=True;code=p.wait()
 finally:
  rm=subprocess.run(['docker','rm','-f',name],capture_output=True);(run/(phase+'-remove.json')).write_text(json.dumps(dict(exit=rm.returncode,stdout=rm.stdout.decode(),stderr=rm.stderr.decode()),indent=2)+'\n')
 text=(run/(phase+'.stdout')).read_text();passed=re.findall(r'^\s*--- PASS: (\S+)',text,re.M);failed=re.findall(r'^\s*--- FAIL: (\S+)',text,re.M);skips=re.findall(r'^\s*--- SKIP: (\S+)',text,re.M);runs=re.findall(r'^=== RUN   (\S+)',text,re.M);assert runs and'no tests to run'not in text and not skips
 match=re.search(r'OCR_DOMAIN_OBSERVATIONS_BEGIN\n(.*?)\nOCR_DOMAIN_OBSERVATIONS_END',text,re.S)
 if match:(run/(phase+'-observations.json')).write_text(match.group(1)+'\n')
 counts=dict(pass_nodes=len(passed),failed=failed,skip=skips,root_runs=[s for s in runs if'/'not in s]);(run/(phase+'-counts.json')).write_text(json.dumps(counts,indent=2)+'\n');row=dict(phase=phase,command=cmd,exit_code=code,seconds=time.monotonic()-start,counts=counts,classification='actual Linux SDK artifact/App/encrypted source config -> owned strict TLS image CONNECT and HTTP OCR service; synthetic-only, no Main/UI/full HDSky/OpenCD');rows.append(row);(run/'commands.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps(dict(phase=phase,exit=code,seconds=row['seconds'],counts=counts)),flush=True)
remaining=subprocess.run(['docker','ps','-aq','--filter','label=task=lm-source-ocr-value-domain-20261106'],capture_output=True);(run/'remaining-containers.txt').write_bytes(remaining.stdout);assert not remaining.stdout.strip()
for n,v in bom.items():assert hashlib.sha256((b/n).read_bytes()).hexdigest()==v['sha256']
(run/'bundle-stable.json').write_text(json.dumps(dict(count=len(bom),same=True,no_containers=True),indent=2)+'\n')
assert rows[0]['exit_code']!=0 and rows[1]['exit_code']!=0 and rows[2]['exit_code']==0,'old/new or native semantic gate failed'
'''.replace('__ROOT__',repr(root)).replace('__MARKER__',repr(marker)).replace('__BOM__',repr(bom))
compile(runner,'remote-runner','exec');(w/'remote-runner.py').write_text(runner);p=subprocess.run(['ssh','admin@192.168.8.129','python3 -'],input=runner.encode(),capture_output=True);(w/'remote-run.stdout').write_bytes(p.stdout);(w/'remote-run.stderr').write_bytes(p.stderr);(w/'remote-command.json').write_text(json.dumps({'argv':['ssh','admin@192.168.8.129','python3 -'],'stdin_sha256':hashlib.sha256(runner.encode()).hexdigest(),'exit':p.returncode},indent=2)+'\n');print(p.stdout.decode());print(p.stderr.decode());print('remote_exit',p.returncode)
x=subprocess.run(['ssh','admin@192.168.8.129','tar -c -f - -C '+shlex.quote(root)+' run-r1'],capture_output=True);assert x.returncode==0
with tarfile.open(fileobj=io.BytesIO(x.stdout),mode='r:')as tar:
 for m in tar.getmembers():assert not m.issym()and not m.islnk()and(w/m.name).resolve().is_relative_to(w.resolve())
 tar.extractall(w,filter='data')
raise SystemExit(p.returncode)
