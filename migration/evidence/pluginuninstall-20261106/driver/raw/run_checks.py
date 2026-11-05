import os,pathlib,json,subprocess,hashlib,time,sys
root=pathlib.Path('/Users/accidia/projects/light-media-plugins'); r=root/'work/migration-20261105/pluginuninstall-main-driver-20261105'
files=['tests/integration/pluginuninstall_main_test.go','tests/integration/pluginuninstall_helpers_test.go','tests/integration/testhost_main_test.go']
env=os.environ.copy();env.pop('GOFLAGS',None);env.pop('PLUGINUNINSTALL_HOST_BINARY',None)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def binding():
 paths=[root/f for f in files]+list((root/'internal/sdk').rglob('*'))+list((root/'plugins/pluginuninstall').rglob('*'))+[root/'cmd/plugin-uninstall/main.go',root/'go.mod',root/'go.sum',root/'SDK_ORIGIN.json',r/'probe/main.go',r/'probe/main_test.go',r/'plugin-version-2.2.1.go',r/'manifest-update-overlay.json']
 return {str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in paths if p.is_file()}
before=binding();results=[]
steps=[
 ('normal',['go','test','-json','-count=1',*files,'-run','TestPluginUninstall']),
 ('race',['go','test','-race','-json','-count=1',*files,'-run','TestPluginUninstall']),
 ('vet',['go','vet',*files]),
 ('probe-normal',['go','test','-json','-count=1','./work/migration-20261105/pluginuninstall-main-driver-20261105/probe']),
 ('probe-race',['go','test','-race','-json','-count=1','./work/migration-20261105/pluginuninstall-main-driver-20261105/probe']),
 ('probe-vet',['go','vet','./work/migration-20261105/pluginuninstall-main-driver-20261105/probe']),
 ('driver-linux',['go','test','-c','-trimpath','-buildvcs=false','-o',str(r/'pluginuninstall-main-linux.test'),*files]),
 ('probe-linux',['go','build','-trimpath','-buildvcs=false','-o',str(r/'owned-pui-fixture-linux'),str(r/'probe/main.go')]),
 ('update-linux',['go','build','-trimpath','-buildvcs=false','-overlay='+str(r/'manifest-update-overlay.json'),'-o',str(r/'plugin-uninstall-2.2.1-linux'),'./cmd/plugin-uninstall']),
 ('probe-native',['go','build','-trimpath','-buildvcs=false','-o',str(r/'owned-pui-fixture'),str(r/'probe/main.go')]),
 ('update-native',['go','build','-trimpath','-buildvcs=false','-overlay='+str(r/'manifest-update-overlay.json'),'-o',str(r/'plugin-uninstall-2.2.1'),'./cmd/plugin-uninstall']),
 ('probe-manifest',[str(r/'owned-pui-fixture'),'--manifest']),
 ('update-manifest',[str(r/'plugin-uninstall-2.2.1'),'--manifest']),
 ('go-env',['go','env','-json','GOVERSION','GOOS','GOARCH','GOFLAGS','GOMOD','GOWORK','CGO_ENABLED']),
]
for name,cmd in steps:
 e=env.copy()
 if name.endswith('-linux'):e.update({'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'})
 start=time.time()
 with open(r/(name+'.stdout'),'wb') as out,open(r/(name+'.stderr'),'wb') as err:
  process=subprocess.run(cmd,cwd=root,env=e,stdout=out,stderr=err)
 results.append({'name':name,'command':cmd,'exit_code':process.returncode,'elapsed_seconds':round(time.time()-start,3),'cross_environment':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'} if name.endswith('-linux') else None})
 (r/'commands.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,process.returncode,flush=True)
 if process.returncode:sys.exit(process.returncode)
after=binding();assert before==after,'source inputs changed during checks'
(r/'check-input-binding.json').write_text(json.dumps({'before':before,'after':after,'all_inputs_stable':True,'GOFLAGS':'unset; no historical overlay; manifest fixture build has explicit absolute overlay only'},indent=2)+'\n')
