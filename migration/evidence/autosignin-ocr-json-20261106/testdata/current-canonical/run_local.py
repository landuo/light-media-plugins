from pathlib import Path
import os,json,subprocess,hashlib,time
P=Path('/Users/accidia/projects/light-media-plugins');H=Path('/Users/accidia/projects/light-media');w=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
env={**os.environ,'GOFLAGS':''}
linux={**env,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'}
records=[]
def run(name,cmd,cwd,e):
 start=time.monotonic();r=subprocess.run(cmd,cwd=cwd,env=e,capture_output=True);(w/(name+'.stdout')).write_bytes(r.stdout);(w/(name+'.stderr')).write_bytes(r.stderr);record={'name':name,'argv':cmd,'cwd':str(cwd),'env':{k:e.get(k)for k in ['GOFLAGS','GOOS','GOARCH','CGO_ENABLED']},'exit':r.returncode,'seconds':time.monotonic()-start};records.append(record);(w/'local-commands.json').write_text(json.dumps(records,indent=2)+'\n');print(json.dumps(record),flush=True);assert r.returncode==0,r.stderr.decode();return r.stdout

def graph(name,cwd,target,overlay,e):
 raw=run(name+'-list',['go','list','-deps','-test','-json','-overlay='+str(overlay),target],cwd,e);decoder=json.JSONDecoder();txt=raw.decode();i=0;packages=[]
 while i<len(txt):
  while i<len(txt)and txt[i].isspace():i+=1
  if i==len(txt):break
  value,i=decoder.raw_decode(txt,i);packages.append(value)
 replacements=json.loads(overlay.read_text())['Replace'];paths={overlay,cwd/'go.mod',cwd/'go.sum'};summaries=[]
 for d in packages:
  directory=Path(d.get('Dir',''));owned=directory.is_relative_to(P)or directory.is_relative_to(H)
  summaries.append({k:d[k]for k in ['ImportPath','Dir','Module','GoFiles','CgoFiles','TestGoFiles','XTestGoFiles','EmbedFiles','TestEmbedFiles','XTestEmbedFiles']if k in d})
  if not owned:continue
  for key in ['GoFiles','CgoFiles','SFiles','HFiles','TestGoFiles','XTestGoFiles','EmbedFiles','TestEmbedFiles','XTestEmbedFiles']:
   for n in d.get(key,[]):
    p=directory/n;p=Path(replacements.get(str(p),str(p)))
    if p.exists():paths.add(p.resolve())
 paths.update(Path(v).resolve()for v in replacements.values())
 (w/(name+'-graph.json')).write_text(json.dumps(summaries,indent=2)+'\n')
 return paths
paths=graph('pure',P,'./plugins/autosignin',w/'pure-overlay.json',env)|graph('probe',P,'./cmd/auto-sign-in',w/'probe-overlay.json',linux)|graph('app',H,'./internal/app',w/'app-overlay.json',linux)
paths.update(w/n for n in ['run_local.py','true-production-binding.json','fixture-source-binding.json'])
snap=lambda:{str(p):sha(p)for p in sorted(paths)}
before=snap();(w/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n')
run('pure-normal',['go','test','-p=1','-json','-count=1','-run=^TestSourceOCRFullJSON(ValueDomain47|MixedDepth9|EmptyDepth4)$','-overlay='+str(w/'pure-overlay.json'),'./plugins/autosignin'],P,env)
run('pure-race',['go','test','-p=1','-race','-json','-count=1','-run=^TestSourceOCRFullJSON(ValueDomain47|MixedDepth9|EmptyDepth4)$','-overlay='+str(w/'pure-overlay.json'),'./plugins/autosignin'],P,env)
run('probe-build',['go','build','-p=1','-trimpath','-buildvcs=false','-ldflags=-s -w','-mod=readonly','-overlay='+str(w/'probe-overlay.json'),'-o',str(w/'current-domain-probe-linux'),'./cmd/auto-sign-in'],P,linux)
run('app-build',['go','test','-p=1','-c','-ldflags=-s -w','-overlay='+str(w/'app-overlay.json'),'-o',str(w/'current-domain-app-linux.test'),'./internal/app'],H,linux)
after=snap();(w/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');assert before==after
(w/'input-stability.json').write_text(json.dumps({'count':len(before),'stable':True,'boundary':'go list -deps -test derived H/P owned files including embed payloads; Go/TestGoFiles included for owned dependency packages (superset). External module versions captured in graphs and checksums in go.sum; noncompiled testdata/Origin/Git metadata not included.'},indent=2)+'\n')
rows=[]
for n in ['current-domain-probe-linux','current-domain-app-linux.test']:
 p=w/n;info=run(n+'-buildinfo',['go','version','-m',str(p)],P,env);rows.append({'path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'buildinfo_sha256':hashlib.sha256(info).hexdigest()})
(w/'binary-provenance.json').write_text(json.dumps(rows,indent=2)+'\n')
for n in ['pure-normal','pure-race']:
 events=[json.loads(line)for line in(w/(n+'.stdout')).read_text().splitlines()];passes=[x['Test']for x in events if x.get('Action')=='pass'and'Test'in x];skips=[x.get('Test')for x in events if x.get('Action')=='skip'];fails=[x.get('Test')for x in events if x.get('Action')=='fail'];assert not skips and not fails and len(passes)==63
 (w/(n+'-counts.json')).write_text(json.dumps({'pass_named':len(passes),'package_pass':sum(x.get('Action')=='pass'and'Test'not in x for x in events),'skip':skips,'failed':fails,'tests':passes},indent=2)+'\n')
print(json.dumps({'complete':True,'inputs':len(before),'stable':True,'binaries':rows}),flush=True)
