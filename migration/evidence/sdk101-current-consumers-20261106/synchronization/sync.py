from pathlib import Path
import json,hashlib,subprocess
r=Path.cwd();host=Path('/Users/accidia/projects/light-media');w=Path(__file__).resolve().parent;old=w/'previous-sdk98';old.mkdir(exist_ok=False);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();origin=r/'SDK_ORIGIN.json';assert sha(origin)=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875';x=json.load(open(origin));assert len(x['files'])==98;(old/'SDK_ORIGIN.json').write_bytes(origin.read_bytes())
commit='b69663ab349de0547c34680a68b66c8486bacd51';changes=x['allowed_changes'];names=['concurrent_session.go','concurrent_transport.go','concurrent_worker.go','protocol.go','worker.go','host_call_budget.go','parallel_host_calls_test.go','parallel_host_calls_independent_test.go'];before={q['path']:q for q in x['files']};mapping={};rows=[]
for name in names:
 source_path='internal/plugins/'+name;target_path='internal/sdk/'+name;src=host/source_path;p=r/target_path;raw=subprocess.check_output(['git','show',commit+':'+source_path],cwd=host);assert src.read_bytes()==raw
 existed=target_path in before
 if existed:
  assert sha(p)==before[target_path]['sha256'];q=old/name;q.write_bytes(p.read_bytes());mapping[str(p)]=str(q);prior=sha(p)
 else:assert not p.exists();mapping[str(p)]='';prior=None
 content=raw;relocations=[]
 for change in changes:
  a=change['from'].encode();b=change['to'].encode()
  if a in content:content=content.replace(a,b);relocations.append(change)
 p.write_bytes(content);row={'source_path':source_path,'path':target_path,'source_sha256':hashlib.sha256(raw).hexdigest(),'sha256':sha(p),'changes':relocations,'source_commit':commit};rows.append(dict(row,before_sha256=prior));before[target_path]=row
for item in before.values():
 assert sha(r/item['path'])==item['sha256']
 raw=subprocess.check_output(['git','show',commit+':'+item['source_path']],cwd=host);assert hashlib.sha256(raw).hexdigest()==item['source_sha256'],item['source_path']
x['source_commit']=commit;x['scope']='101 complete SDK/test/fixture files: previous98 plus1 opt-in reverse-call budget helper and2 actual parallel regressions;5 previous productionfiles changed. Full files match committed host plus only2 declared import relocations; no host App/business implementation copied. Existing legacy workers remain serial unless they explicitly opt in.';x['files']=sorted(before.values(),key=lambda q:q['path']);assert len(x['files'])==101
origin.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');(w/'previous-sdk98-overlay.json').write_text(json.dumps({'Replace':mapping},indent=2)+'\n');(w/'synchronization.json').write_text(json.dumps({'classification':'exact standaloneSDK synchronization from saved independently reviewed host code; current consumer rebuild/nativeimpact/ASI still pending','old_origin_sha256':sha(old/'SDK_ORIGIN.json'),'new_origin_sha256':sha(origin),'source_commit':commit,'files_before':98,'files_after':len(x['files']),'source_difference':'five old productionfiles changed;new host_call_budget helper plus2newtests. Earlier shorthand sixSDK includes budgetnew,not6oldchanged.','old98_overlay':str(w/'previous-sdk98-overlay.json'),'rows':rows,'all101_committed_source_bytes_verified':True},indent=2)+'\n');print(json.dumps({'files':len(x['files']),'origin_sha256':sha(origin),'host_source_commit':commit,'old98_saved':True}))
