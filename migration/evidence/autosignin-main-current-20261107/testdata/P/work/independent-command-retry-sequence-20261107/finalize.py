from pathlib import Path
import hashlib,json,subprocess
w=Path(__file__).resolve().parent;p=w.parent.parent;old=p/'work/independent-source-main-contract-20261107'
hashfile=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert hashfile(old/'freeze.json')=='965068464af1bf76e955e73f747f8f66d9df6fd187fc88733c777090e72479b9'
sources=json.loads((w/'sources.json').read_text());checks=[]
for name,text in sources.items():
 if name.startswith('app/'):
  raw=subprocess.check_output(['git','show','8a83efeacd3e26b82be495e17d50146e31c96a60:'+name],cwd='/Users/accidia/projects/MoviePilot')
 else:raw=(old/name).read_bytes()
 assert raw==text.encode(),name
 checks.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'binding':'fixed8a Git blob'if name.startswith('app/')else'installed270 snapshot exact old965'})
assert next(x for x in checks if x['path']=='installed-asi/__init__.py')['sha256']=='1d8329afc00bc218710e302e0eda915351731d41101df08fcf378e90440b9220'
assert (w/'body-prefix.py').read_text()==(old/'message-body.py').read_text().split('for notify in [False,True]:\n',1)[0]
(w/'source-binding-check.json').write_text(json.dumps({'old_seal_sha256':hashfile(old/'freeze.json'),'old_source_unchanged':True,'prefix_is_exact_frozen_message_prefix':True,'checks':checks},indent=2)+'\n')
d=json.loads((w/'actual.stdout').read_text());cmd=json.loads((w/'command.json').read_text());assert cmd['exit']==0
summary={'source_classification':d['classification'],'messages':[r['message_count']for r in d['rows']],'attendance':[r['attendance_total']for r in d['rows']],'calls_base_clone':[r['calls_after']for r in d['rows']],'completion_messages':[sum(x.get('title')=='站点签到完成！'for x in r['new_messages'])for r in d['rows']],'negative_without_reset':{'calls':d['negative']['calls'],'titles':[p['title']for p in d['negative']['posts']]},'source_files':len(checks),'source_exit':cmd['exit'],'seconds':cmd['seconds'],'target_Main_runs':0,'true_writes':0,'old_DB_reads':0}
assert summary['messages']==[3,8,13,16]and summary['attendance']==[2,4,6,6]
(w/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
remote="docker ps -aq --filter label=migration.review=independent-command-retry-sequence-20261107"
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','admin@192.168.8.129',remote],capture_output=True,timeout=15)
(w/'cleanup-observation.json').write_text(json.dumps({'argv':['ssh','admin@192.168.8.129',remote],'exit':r.returncode,'stdout':r.stdout.decode(),'stderr':r.stderr.decode(),'classification':'exact owned label readback; Docker --rm source-only no-bind container'},indent=2)+'\n')
assert r.returncode==0 and not r.stdout.strip()
print(json.dumps(summary,ensure_ascii=False))
