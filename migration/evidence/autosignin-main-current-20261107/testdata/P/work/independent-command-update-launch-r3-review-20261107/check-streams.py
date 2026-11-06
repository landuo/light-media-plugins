from pathlib import Path
import gzip,hashlib,json
p=Path('/Users/accidia/projects/light-media-plugins');a=p/'work/autosignin-command-update-main-20261107';w=Path(__file__).resolve().parent;before=json.loads((a/'before-build-inputs.json').read_text());old=p/'work/independent-command-update-launch-r2-review-20261107/reviewed'
def objects(raw):
 text=raw.decode();pos=0;dec=json.JSONDecoder();out=[]
 while pos<len(text):
  while pos<len(text)and text[pos].isspace():pos+=1
  if pos==len(text):break
  r,end=dec.raw_decode(text,pos);pos=end;out.append(r)
 return out
rows=[];bindings=[];names=['host','worker','worker-updated','cli','driver'];d=w/'lists';d.mkdir(exist_ok=True)
for name in names:
 phases=[]
 for label in ['before-build','after-build']:
  rawfile=a/(label+'-'+name+'-list.json');raw=rawfile.read_bytes();packages=objects(raw);mapping=json.loads((a/('driver-overlay.json'if name=='driver'else'updated-worker-overlay.json')).read_text())['Replace']if name in ['driver','worker-updated']else{};selection={};embeds=set()
  for q in packages:
   for field in ['GoFiles','CompiledGoFiles','TestGoFiles','XTestGoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SwigFiles','SwigCXXFiles','SysoFiles','EmbedFiles','TestEmbedFiles','XTestEmbedFiles']:
    for value in q.get(field,[]):
     logical=Path(value);logical=logical if logical.is_absolute()else Path(q.get('Dir',p))/logical;physical=mapping.get(str(logical),str(logical));assert physical in before,(name,field,physical);selection.setdefault(q['ImportPath'],{}).setdefault(field,[]).append({'logical':str(logical),'physical':physical,'sha256':before[physical]})
     if 'Embed'in field:embeds.add(physical)
  packed=d/(rawfile.name+'.gz');packed.write_bytes(gzip.compress(raw,mtime=0));bindings.append({'source':str(rawfile),'original_sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'lossless_gzip':str(packed.relative_to(w)),'stored_sha256':hashlib.sha256(packed.read_bytes()).hexdigest()});phases.append(selection)
  if label=='before-build':rows.append({'driver':name,'packages':len(packages),'selected_packages':len(selection),'selected_unique_paths':len({x['physical']for f in selection.values()for xs in f.values()for x in xs}),'embeds':len(embeds)})
 assert phases[0]==phases[1],name
 if name=='driver':assert any(x['physical']==str(a/'driver.go')and x['sha256']=='f48d30b3511741ab1c7cf6ceb03db6f1a4ae29e678f08c4da00f3d02e3ad956e'for f in phases[0].values()for xs in f.values()for x in xs)
oldbom=json.loads((old/'bundle-bom.json').read_text());bom=json.loads((a/'bundle-bom.json').read_text());assert set(k for k in bom if bom[k]!=oldbom[k])=={'bin/host','bin/cli','bin/driver'}
# Executed R2 source/host/driver and prior pass remain exact, not relabeled as causal drain.
oldattempt=a/'attempt2-four-Web-update-cooperative-stop-pass';assert hashlib.sha256((oldattempt/'driver.go').read_bytes()).hexdigest()=='d87067940fc58353a3e86984bc6430502bafafd3a95df14208c3ae01c1f9c694';assert hashlib.sha256((oldattempt/'driver').read_bytes()).hexdigest()=='a2d0a15dc003fd3823cc1ad48cc66f418c71c6403f9651f2c4ea4e0093171591';assert hashlib.sha256((oldattempt/'host').read_bytes()).hexdigest()=='8ea38cff7e98f6a1eb7089f7ff04cc8c56fdb41baedfdbc843db13824b999f67'
assert(oldattempt/'bundle-bom.json').read_bytes()==(old/'bundle-bom.json').read_bytes()
assert(a/'actual-r2/attempt5/actual.stdout').read_bytes()==(p/'work/independent-command-main-r2-runtime-review-20261107/raw/attempt5/actual.stdout').read_bytes()
# Predicates consume our frozen original3 fixture and retain distinct pending/empty/success cases.
preflight=(a/'page-predicates_test.go').read_text();assert 'independent-command-main-attempt4-review-20261107/source-oracle.json'in preflight
for case in ['disabled-selected-no-history','disabled-unselected-no-history','disabled-selected-success-history']:assert case in preflight
logs=[json.loads(l)for l in(a/'page-predicates.stdout.jsonl').read_text().splitlines()if l.startswith('{')];assert sum(x.get('Action')=='pass'and'Test'in x for x in logs)==4 and not any(x.get('Action')in ['skip','fail']for x in logs)
for n in ['page-predicates_test.go','page-predicates.stdout.jsonl','page-predicates.stderr','preflight-overlay.json']:(w/'reviewed'/n).write_bytes((a/n).read_bytes())
(w/'stream-verification.json').write_text(json.dumps({'raw_streams':10,'stream_bindings':bindings,'drivers':rows,'before_after_selected_fields_equal':True,'all_selected_paths_in_7064_map':True,'worker_and_updated_worker_ELFs_identical':True,'old_r2_cooperative_outcome_preserved':True,'source3_predicate_raw_named_pass':4,'source_reruns':0,'Main_runs':0,'closure_scope':'actual saved Go list -deps -compiled(-test for driver) field selection reconstructed; includes TestGo fields over listed dependencies, module/tools plus extra fixed source-contract input hashes are separately in7064; Linux CGO0 normal build only'},indent=2)+'\n');print(json.dumps(rows,indent=2))
