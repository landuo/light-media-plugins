from pathlib import Path
import subprocess,os,json,hashlib,time
P=Path('/Users/accidia/projects/light-media-plugins');H=P.parent/'light-media';W=Path(__file__).resolve().parent;env={**os.environ,'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0','GOFLAGS':'','GOPROXY':'off'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def graph(root,pkg,name):
 args=['go','list','-deps','-compiled','-json',pkg];r=subprocess.run(args,cwd=root,env=env,capture_output=True);(W/(name+'-graph.stdout')).write_bytes(r.stdout);(W/(name+'-graph.stderr')).write_bytes(r.stderr);assert r.returncode==0
 text=r.stdout.decode();dec=json.JSONDecoder();at=0;files=set();embeds=set()
 while at<len(text):
  while at<len(text)and text[at].isspace():at+=1
  if at>=len(text):break
  obj,at=dec.raw_decode(text,at);directory=Path(obj.get('Dir',root))
  for key in ['GoFiles','CompiledGoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SwigFiles','SwigCXXFiles','SysoFiles','EmbedFiles']:
   for value in obj.get(key,[]):
    p=Path(value);p=p if p.is_absolute()else directory/p;assert p.is_file(),str(p);files.add(p)
    if key=='EmbedFiles':embeds.add(p)
  if obj.get('Module',{}).get('GoMod'):files.add(Path(obj['Module']['GoMod']))
 for f in [root/'go.mod',root/'go.sum']:files.add(f)
 tool=Path(subprocess.check_output(['go','env','GOTOOLDIR'],cwd=root,env=env,text=True).strip())
 for name in ['compile','link','asm']:files.add(tool/name)
 return files,embeds
allfiles=set();embeds=set()
for name,root,pkg in [('host',H,'./cmd/server'),('worker',P,'./cmd/auto-sign-in')]:
 f,e=graph(root,pkg,name);allfiles|=f;embeds|=e
before={str(p):sha(p)for p in sorted(allfiles)};(W/'before.json').write_text(json.dumps(before,indent=2)+'\n');(W/'embeds.json').write_text(json.dumps({str(p):sha(p)for p in sorted(embeds)},indent=2)+'\n')
rows=[]
for name,root,pkg,expected in [('host',H,'./cmd/server','b0a9a175e3b6d61b1a9158d4638f9a3c6639291f93879da11f5cbf157e5c6963'),('worker',P,'./cmd/auto-sign-in','a4524236b3bad3462f640958ad56a170759558d69ff038ce56953ba38f648918')]:
 out=W/name;args=['go','build','-p=1','-trimpath','-buildvcs=false','-ldflags=-s -w','-o',str(out),pkg];t=time.monotonic();r=subprocess.run(args,cwd=root,env=env,capture_output=True);(W/(name+'-build.stdout')).write_bytes(r.stdout);(W/(name+'-build.stderr')).write_bytes(r.stderr);assert r.returncode==0;actual=sha(out);rows.append({'name':name,'argv':args,'cwd':str(root),'exit':r.returncode,'seconds':time.monotonic()-t,'sha256':actual,'expected_prior_actual_Main_ELF':expected,'byte_identical':actual==expected});assert actual==expected
 r=subprocess.run(['go','version','-m',str(out)],capture_output=True);assert r.returncode==0;(W/(name+'.buildinfo.txt')).write_bytes(r.stdout)
after={str(p):sha(p)for p in sorted(allfiles)};(W/'after.json').write_text(json.dumps(after,indent=2)+'\n');record={'actual_fresh_build':rows,'stable':before==after,'inputs':len(before),'embed_files':len(embeds),'env':{k:env[k]for k in ['GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOPROXY']},'source_scope':'Actualgo-list deps/compiled productionH/P includingallmodule/source/embed/toolchaininputs. OriginalMain/UI runs retaintheir original tracked-only lists; thisnewfresh deterministic rebuildmatchesexact executedELFs, notfakehistoricalbefore/after.','original_binary_paths':'P/work/autosignin-owned-main-20261106-r5/{host,worker}','frontend':'web/src cloneprefill changes notbuiltinto oldweb/dist yet; thiscapture bindsoldactual Main56dUI, notfuturebundle.'};(W/'reproduction.json').write_text(json.dumps(record,indent=2)+'\n');assert before==after;print(json.dumps({'stable':record['stable'],'inputs':len(before),'embeds':len(embeds),'identical_ELFs':len(rows)}))
