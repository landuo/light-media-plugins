from pathlib import Path
import json,subprocess,hashlib,os,time
r=Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/pui-current-driver';b=r/'work/migration-20261105/removelink-main6-20261106/driver-build-binding.json';binding=json.loads(b.read_text());old_expected=binding['binary_sha256'];env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
h=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
def inputs():
 files={}
 for f in sorted((r/'tests/integration').glob('*.go')):files[str(f.relative_to(r))]=h(f)
 assert len(files)==16,len(files)
 for f in sorted((r/'internal/sdk').rglob('*')):
  if f.is_file():files[str(f.relative_to(r))]=h(f)
 for name in ['go.mod','go.sum','SDK_ORIGIN.json']:files[name]=h(r/name)
 return files
before=inputs();assert before['SDK_ORIGIN.json']=='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
for file,oldhash in binding['inputs_before'].items():
 if file!='tests/integration/pluginuninstall_main_test.go':assert before[file]==oldhash,file
(p/'inputs-before.json').write_text(json.dumps(before,indent=2)+'\n');commands=[]
for name,overlay in [('pluginuninstall-current-main-linux.test',False),('removelink-f24-reproduced-linux.test',True)]:
 argv=list(binding['command']);argv[argv.index('-o')+1]=str(p/name)
 if overlay:argv.insert(4,'-overlay='+str(p/'old-f24-single-file-overlay.json'))
 start=time.monotonic()
 with (p/(name+'.stdout')).open('w') as out,(p/(name+'.stderr')).open('w') as err:s=subprocess.run(argv,cwd=r,env=env,stdout=out,stderr=err)
 commands.append({'argv':argv,'cwd':str(r),'explicit_env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'exit':s.returncode,'elapsed_seconds':time.monotonic()-start});assert s.returncode==0
 if overlay:assert h(p/name)==old_expected,(h(p/name),old_expected)
 (p/(name+'.buildinfo.txt')).write_text(subprocess.check_output(['go','version','-m',str(p/name)],cwd=r,text=True))
after=inputs();assert before==after
(p/'inputs-after.json').write_text(json.dumps(after,indent=2)+'\n');(p/'commands.json').write_text(json.dumps(commands,indent=2)+'\n')
artifacts=[{'path':str(p/name),'sha256':h(p/name),'bytes':(p/name).stat().st_size,'old_f24_reproduced':overlay} for name,overlay in [('pluginuninstall-current-main-linux.test',False),('removelink-f24-reproduced-linux.test',True)]]
(p/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n');(p/'toolchain.json').write_text(subprocess.check_output(['go','env','-json','GOOS','GOARCH','CGO_ENABLED','GOVERSION','GOFLAGS'],cwd=r,text=True))
print(json.dumps({'input_count':len(before),'integration_files':16,'artifacts':artifacts},indent=2))
