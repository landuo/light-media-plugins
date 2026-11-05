from pathlib import Path
import json,hashlib,collections,re,subprocess
root=Path('/Users/accidia/projects/light-media-plugins');host=Path('/Users/accidia/projects/light-media');out=Path(__file__).resolve().parent;sha=lambda b:hashlib.sha256(b).hexdigest();report={}
def valid(path,expect=None):
 b=path.read_bytes();h=sha(b)
 if expect:assert h==expect,(str(path),h,expect)
 return {'path':str(path),'sha256':h,'bytes':len(b)}
raw=root/'work/migration-20261105/pluginuninstall-main-runtime-20261106/actual-harvest';manifest=raw/'manifest.json';valid(manifest,'da452273d94730fd218e0841080feebcd27dbc4c85e5e7c879c58cb1a9d6d76c');m=json.loads(manifest.read_text());report['harvest']=valid(manifest)
for r in m['files']:assert valid(raw/r['path'])['sha256']==r['sha256']
assert len(m['files'])==23;report['harvest_files']=23
pins=[(root/'work/migration-20261105/pluginuninstall-20261105/private-files-final.json','090159b7a56b9629871055d49cc6bf8afe605c8516eb6d93c09fb06ce6dffd0c',root),(host/'work/pluginuninstall-source-startup-20261105/host-files-current.json','f9e4f90ef62309f4b064dbeb8f9a3b319841dd2c4c6e9bd33aa16201fb022988',host)]
for p,h,r in pins:
 valid(p,h);d=json.loads(p.read_text());
 if isinstance(d,dict):print('manifest keys',str(p),list(d)[:8])
 rows=d if isinstance(d,list) else d.get('files',[])
 for row in rows:assert valid(r/row['path'])['sha256']==row['sha256'],row['path']
 report[str(p)]=len(rows)
origin=root/'SDK_ORIGIN.json';valid(origin,'40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875')
for row in json.loads(origin.read_text())['files']:assert valid(root/row['path'])['sha256']==row['sha256']
report['sdk98_current_matched']=98
bind=root/'work/migration-20261105/shared-host-pluginuninstall-reviewed/host-pluginuninstall-reviewed-build-source-binding.json';b=json.loads(bind.read_text());assert b['before']==b['after'] and b['repository_inputs']==1838 and b['binary_sha256']=='8305d765055b80f80bdcdc7ad8cfc14857da24c5abcccd54d9ec4e1c6b65fd7b'
# Audit the saved build binding against the original Git object database, avoiding today's mutable host checkout.
errors=[];frozen=0;gitbound=0
for path,r in b['before'].items():
 if r.get('frozen_PUI_increment'):
  frozen+=1;continue
 if r.get('git_blob')!=r.get('actual_blob'):errors.append((path,'blob mismatch'));continue
 blob=r.get('git_blob')
 if not blob:errors.append((path,'missing blob'));continue
 data=subprocess.check_output(['git','cat-file','blob',blob],cwd=host)
 if sha(data)!=r['sha256']:errors.append((path,'hash mismatch'))
 gitbound+=1
assert not errors,errors[:4]
assert len(b['before'])==1838
report['host_build_binding']={'record':valid(bind),'base_revision':b['base_revision'],'inputs':1838,'Gitblob_matched':gitbound,'frozen_PUI_increment':frozen,'before_after_equal':True,'ELF':b['binary_sha256']}
for role,path in [('PUI',raw/'pui/main-run-1/runtime/evidence/observations.jsonl'),('IMPACT5',raw/'impact/main-run-5/evidence/observations.jsonl')]:
 rows=[json.loads(l) for l in path.read_text().splitlines()];counts=collections.Counter(r['event'] for r in rows)
 report[role]={'rows':len(rows),'events':dict(counts)}
 if role=='PUI':
  complete=[r['value'] for r in rows if r['event']=='pui_main_complete'];assert len(complete)==1 and complete[0]['UI_executed'] is True and complete[0]['all_observed_workers_joined']==35
  assert counts['main_start']==counts['main_exit']==8
  assert all(r['value']['error']=='<nil>' for r in rows if r['event']=='main_exit')
  status=collections.Counter(r['value']['status'] for r in rows if r['event']=='pui_http');assert status[404]==1 and status[500]==2
  report[role].update(HTTP_statuses=dict(status),complete=complete[0])
 else:
  starts=[r['value']['main_sha256'] for r in rows if r['event']=='sdk98_main_start'];assert starts==['8305d765055b80f80bdcdc7ad8cfc14857da24c5abcccd54d9ec4e1c6b65fd7b']*2
  complete=next(r['value'] for r in rows if r['event']=='sdk98_four_instance_complete');assert complete['qB']['completed_queries']==4 and complete['qB']['unexpected_or_mutation_requests']==[] and complete['Nexus']['unexpected']==[]
  assert next(r['value'] for r in rows if r['event']=='sdk98_impact_on_return')['test_failed'] is False
  report[role]['stale_classification_text']='raw says ordinary f7 Main; actual command and two runtime SHA records unequivocally8305; preserve raw and qualify'
# An independent recursive secret-shaped-value scan, count only; never print potential values.
pattern=re.compile(rb'(?i)"(?:password|api_token|authorization|cookie|apikey)"\s*:\s*"(?!\[redacted\])[^"\s]+')
finds=[r['path'] for r in m['files'] if pattern.search((raw/r['path']).read_bytes())];assert finds==[],finds;report['harvest_secret_shape_matches']=0
(out/'checks.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');print(json.dumps(report,ensure_ascii=False))
