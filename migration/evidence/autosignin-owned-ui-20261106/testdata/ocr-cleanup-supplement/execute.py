from pathlib import Path
import json,hashlib,subprocess,datetime
w=Path(__file__).resolve().parent;plan=json.loads((w/'plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
script='''from pathlib import Path
import json,hashlib,subprocess,os,datetime
phases=PHASES
results=[]
for phase in phases:
 r=Path(phase['root']);assert r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text().strip()==phase['marker']
 result={'root':str(r),'label':phase['label'],'marker_equal':True,'deleted':[]}
 for row in phase['files']:
  p=r/row['relative'];assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(r.resolve());assert p.stat().st_size==row['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 labels=subprocess.run(['docker','ps','-aq','--filter','label=task='+phase['label']],capture_output=True);assert labels.returncode==0 and not labels.stdout.strip();result['own_containers']=0
 held=[]
 for d in Path('/proc').iterdir():
  if not d.name.isdigit():continue
  for key in ['exe','cwd']:
   try:
    target=os.readlink(d/key)
    if target==str(r)or target.startswith(str(r)+'/'):held.append({'pid':d.name,'kind':key,'path':target})
   except OSError:pass
  try:fds=list((d/'fd').iterdir())
  except OSError:continue
  for fd in fds:
   try:
    target=os.readlink(fd)
    if target==str(r)or target.startswith(str(r)+'/'):held.append({'pid':d.name,'kind':'fd','path':target})
   except OSError:pass
 assert not held,held;result['proc_exe_cwd_fd_matches']=[]
 for row in phase['files']:
  p=r/row['relative'];p.unlink();assert not p.exists();result['deleted'].append(row)
 result['bytes_deleted']=sum(x['bytes']for x in result['deleted']);results.append(result)
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'only exact owned released JSON ELF files; source/oracles/raw/frozen manifests and recipes untouched','results':results},ensure_ascii=False))
'''.replace('PHASES',repr(plan['remote']));(w/'remote-execute.py').write_text(script)
r=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],input=script.encode(),capture_output=True);(w/'remote.stdout').write_bytes(r.stdout);(w/'remote.stderr').write_bytes(r.stderr);(w/'remote-command.json').write_text(json.dumps({'argv':['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3','-'],'payload_sha256':hashlib.sha256(script.encode()).hexdigest(),'exit':r.returncode},indent=2)+'\n');assert r.returncode==0,r.stderr.decode()
lsof=subprocess.run(['lsof','-Fpn','--',*[x['path']for x in plan['local']]],capture_output=True);(w/'local-final-lsof.stdout').write_bytes(lsof.stdout);(w/'local-final-lsof.stderr').write_bytes(lsof.stderr);assert lsof.returncode==1 and not lsof.stdout
for row in plan['local']:
 p=Path(row['path']);assert p.is_file()and not p.is_symlink()and sha(p)==row['sha256']and p.stat().st_size==row['bytes']
for row in plan['local']:
 p=Path(row['path']);p.unlink();assert not p.exists()
result={'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'local_files_deleted':len(plan['local']),'local_bytes_deleted':sum(x['bytes']for x in plan['local']),'remote_files_deleted':sum(len(x['files'])for x in plan['remote']),'remote_bytes_deleted':sum(y['bytes']for x in plan['remote']for y in x['files']),'original_provenance_manifests_preserved':all(sha(Path(x['provenance_path']))==x['provenance_sha256']for x in plan['remote']),'production_mutations':False,'binary_files_only':True};assert result['original_provenance_manifests_preserved'];(w/'result.json').write_text(json.dumps(result,indent=2)+'\n')
files=[p for p in sorted(w.iterdir())if p.is_file()and p.name!='seal.json'];(w/'seal.json').write_text(json.dumps({'schema':1,'scope':'explicit Root-released author/canonical JSON ELF cleanup with exact byte/marker/proc/container guards','files':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size}for p in files]},indent=2)+'\n');print(json.dumps({'result':result,'seal_sha256':sha(w/'seal.json')}))
