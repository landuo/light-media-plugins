from pathlib import Path
import subprocess,json,os,time,hashlib,sys
out=Path(__file__).resolve().parent;root=Path('/Users/accidia/projects/light-media-plugins');sha=lambda b:hashlib.sha256(b).hexdigest()
env=os.environ.copy();env.update(GOFLAGS='',TMPDIR=str(out/'tmp'),REMOVELINK_LOG_OBSERVATIONS=str(out/'log-observations'))
command=['go','list','-overlay',str(out/'overlay.json'),'-deps','-test','-json','./plugins/removelink','./cmd/remove-link']; p=subprocess.run(command,cwd=root,env=env,capture_output=True);(out/'list.jsonstream').write_bytes(p.stdout);(out/'list.stderr').write_bytes(p.stderr);assert p.returncode==0
text=p.stdout.decode();decoder=json.JSONDecoder();ps=[]
while text.strip():
 text=text.lstrip();obj,n=decoder.raw_decode(text);ps.append(obj);text=text[n:]
paths=set()
for obj in ps:
 if obj.get('Standard'):continue
 d=Path(obj.get('Dir',''))
 for field in ['GoFiles','CgoFiles','CFiles','HFiles','SFiles','EmbedFiles','TestGoFiles','XTestGoFiles','TestEmbedFiles','XTestEmbedFiles']:
  for name in obj.get(field,[]):
   p=d/name
   if p.is_file():paths.add(str(p))
for name in ['go.mod','go.sum','SDK_ORIGIN.json']:paths.add(str(root/name))
def snap():
 return {p:{'bytes':Path(p).stat().st_size,'sha256':sha(Path(p).read_bytes())} for p in sorted(paths)}
before=snap();(out/'compile-inputs-before.json').write_text(json.dumps(before,indent=2)+'\n')
records=[]
for label,extra in [('full-normal',[]),('full-race',['-race'])]:
 cmd=['go','test','-overlay',str(out/'overlay.json'),'-count=1','-json']+extra+['./plugins/removelink','./cmd/remove-link'];start=time.time()
 with (out/(label+'.jsonl')).open('wb') as stdout,(out/(label+'.stderr')).open('wb') as stderr:
  proc=subprocess.run(cmd,cwd=root,env=env,stdout=stdout,stderr=stderr)
 rows=[]
 for line in (out/(label+'.jsonl')).read_text().splitlines():
  try:rows.append(json.loads(line))
  except:pass
 counts={k:sum(r.get('Action')==k and bool(r.get('Test')) for r in rows) for k in ['pass','fail','skip']}
 rec={'label':label,'command':cmd,'exit':proc.returncode,'elapsed':time.time()-start,'counts':counts,'package_results':[r for r in rows if not r.get('Test') and r.get('Action') in ['pass','fail','skip']]};records.append(rec)
 (out/'executed-commands.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(rec),flush=True)
 if proc.returncode:break
 after=snap();(out/'compile-inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after
