from pathlib import Path
import os,json,hashlib,subprocess,time
r=Path('/Users/accidia/projects/light-media-plugins');hroot=Path('/Users/accidia/projects/light-media');p=r/'work/migration-20261106/removelink-business-main-preparation';env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0');hashf=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def go_inputs(root, package):
 raw=subprocess.check_output(['go','list','-deps','-json',package],cwd=root,env=env,text=True)
 decoder=json.JSONDecoder();pos=0;files={};packages=[]
 while pos<len(raw):
  while pos<len(raw) and raw[pos].isspace():pos+=1
  if pos==len(raw):break
  package,pos=decoder.raw_decode(raw,pos)
  if package.get('Standard'):continue
  names=[]
  for field in ['GoFiles','CgoFiles','CFiles','CXXFiles','MFiles','HFiles','FFiles','SFiles','SysoFiles','EmbedFiles']:names.extend(package.get(field,[]))
  for name in names:
   source=Path(package['Dir'])/name
   files[str(source)]=hashf(source)
  packages.append({'import_path':package['ImportPath'],'directory':package['Dir'],'files':names,'module':package.get('Module')})
 for name in ['go.mod','go.sum']:files[str(root/name)]=hashf(root/name)
 return files,packages
notice_files,notice_packages=go_inputs(hroot,'./cmd/owned-notice-fixture')
(p/'notice-build-closure.json').write_text(json.dumps({'files':notice_files,'packages':notice_packages},indent=2)+'\n')
def inputs():
 files=dict(notice_files)
 for f in sorted((r/'tests/integration').glob('*.go')):files[str(f)]=hashf(f)
 assert len(list((r/'tests/integration').glob('*.go')))==17
 for f in sorted((r/'internal/sdk').rglob('*')):
  if f.is_file():files[str(f)]=hashf(f)
 for n in ['go.mod','go.sum','SDK_ORIGIN.json']:files[str(r/n)]=hashf(r/n)
 for n in ['store.go','plugin_notice_storage.go','core_source_primitives.go','plugin_store.go','http.go','import_plan.go','import_run.go','jobs.go','plugin_original_notice.go']:files[str(hroot/'internal/app'/n)]=hashf(hroot/'internal/app'/n)
 return files
before=inputs();(p/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');commands=[]
def run(argv,cwd,out,err,envOverride=env):
 start=time.monotonic()
 with Path(out).open('w') as o,Path(err).open('w') as e:s=subprocess.run(argv,cwd=cwd,env=envOverride,stdout=o,stderr=e)
 commands.append({'argv':argv,'cwd':str(cwd),'explicit_env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'exit':s.returncode,'elapsed_seconds':time.monotonic()-start});assert s.returncode==0,argv
binary=p/'removelink-business-main-linux.test';run(['go','test','-tags=removelink_business_acceptance','-c','-trimpath','-buildvcs=false','-o',str(binary),'./tests/integration'],r,p/'driver-build.stdout',p/'driver-build.stderr')
# The default package still excludes the new file. Rebuild current PUI driver
# without tags as a narrow proof; never overwrite/relabel Root's old f24 run.
default=p/'default-current-driver-proof.test';run(['go','test','-c','-trimpath','-buildvcs=false','-o',str(default),'./tests/integration'],r,p/'default-build.stdout',p/'default-build.stderr');assert hashf(default)=='01ba473ce2aeb5da61c299dded7a7be74cc22816a9a9f3c4edcb2e8cc26dd57b';default.unlink()
notice=p/'owned-notice-fixture-linux';run(['go','build','-trimpath','-buildvcs=false','-o',str(notice),'./cmd/owned-notice-fixture'],hroot,p/'notice-build.stdout',p/'notice-build.stderr')
notice_after,_=go_inputs(hroot,'./cmd/owned-notice-fixture');assert notice_files==notice_after
after=inputs();assert before==after;(p/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n')
for f in [binary,notice]:(p/(f.name+'.buildinfo.txt')).write_text(subprocess.check_output(['go','version','-m',str(f)],text=True,cwd=r))
(p/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');artifacts=[{'path':str(f),'sha256':hashf(f),'bytes':f.stat().st_size}for f in [binary,notice]];(p/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n')
(p/'default-tag-exclusion-proof.json').write_text(json.dumps({'default_build_SHA256':'01ba473ce2aeb5da61c299dded7a7be74cc22816a9a9f3c4edcb2e8cc26dd57b','default_duplicate_removed':True,'new_file_default_ignored':True,'Root_f24_not_modified_or_relabelled':True},indent=2)+'\n')
print(json.dumps(artifacts,indent=2))
