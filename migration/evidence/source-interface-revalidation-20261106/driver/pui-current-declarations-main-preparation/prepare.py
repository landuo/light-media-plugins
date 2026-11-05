from pathlib import Path
import subprocess,json,hashlib,os,time
r=Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/pui-current-declarations-main-preparation';old=r/'work/migration-20261105/pluginuninstall-main-driver-20261105';probe=old/'probe/main.go'
hashf=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()
sdk_expected='40e923e3a50de325e49fe9e7c88709295286c91a8c23e141b33b5bad6e35a875'
assert hashf(r/'SDK_ORIGIN.json')==sdk_expected
assert hashf(probe)=='6cc20daad968ab46bbc0c5f7049db2da08558153e249968f7b2fba66895d47c6'
assert probe.read_bytes()==(old/'frozen-driver-source/probe-main.go').read_bytes()
legacy_commands=json.loads((old/'commands.json').read_text());original_probe=next(x for x in legacy_commands if x['name']=='probe-linux');assert original_probe['command'][-1]==str(probe)
source=r/'plugins/pluginuninstall/plugin.go';s=source.read_text();assert s.count('Version: "2.2"')==1
update=p/'plugin-version-2.2.1.go';update.write_text(s.replace('Version: "2.2"','Version: "2.2.1"',1));assert update.read_text().replace('Version: "2.2.1"','Version: "2.2"',1)==s
overlay=p/'version-overlay.json';overlay.write_text(json.dumps({'Replace':{str(source):str(update)}},indent=2)+'\n')
(p/'TASK.json').write_text(json.dumps({'owner':'/root/plugin_sdk','scope':'Local compile/binding only for Root PUI Main2 SKIP_UI=1; no product edits/NAS/Main/private UI-ready/DB','SDK_ORIGIN_sha256':sdk_expected,'old_probe_source_sha256':hashf(probe),'legacy_probe_command':original_probe},indent=2)+'\n')
env=os.environ.copy();env.update(GOOS='linux',GOARCH='amd64',CGO_ENABLED='0')
fmt='{{if .Module}}{{if .Module.Main}}{{.Dir}}|{{join .GoFiles ","}}|{{join .EmbedFiles ","}}{{end}}{{end}}'
def binding(package,replacements=None):
 argv=['go','list']+(['-overlay='+str(overlay)] if replacements else[])+['-deps','-f',fmt,package]
 raw=subprocess.check_output(argv,cwd=r,env=env,text=True);out={}
 for line in raw.splitlines():
  if not line:continue
  d,*groups=line.split('|')
  for group in groups:
   for name in group.split(','):
    if not name:continue
    file=Path(d)/name;actual=(replacements or{}).get(str(file),str(file));out[str(file)]={'actual_source':actual,'sha256':hashf(actual)}
 if package==str(probe):out[str(probe)]={'actual_source':str(probe),'sha256':hashf(probe)}
 for name in ['go.mod','go.sum','SDK_ORIGIN.json']:out[str(r/name)]={'actual_source':str(r/name),'sha256':hashf(r/name)}
 return out
plans=[('plugin-uninstall-linux','./cmd/plugin-uninstall',None,'d001e6796321b8a7702aad9fe9c4785f2ad349c5b3d19b0008ed8d0440e0dbc3'),('mp-server-status-linux','./cmd/mp-server-status',None,'32780c52accebb11329d9e54aea09c6dcc124f92532c1fd882e203b8aa8a793d'),('plugin-uninstall-2.2.1-linux','./cmd/plugin-uninstall',{str(source):str(update)},None),('owned-pui-fixture-linux',str(probe),None,'b4d23deb2ba9d58dbd30dc56d6f212c5498cad35272160716dc0c85650ec7744')]
before={name:binding(pkg,rep) for name,pkg,rep,_ in plans};(p/'compile-inputs-before.json').write_text(json.dumps(before,indent=2)+'\n')
commands=[];artifacts=[]
for name,pkg,rep,expected in plans:
 binary=p/name
 if name=='owned-pui-fixture-linux':
  argv=list(original_probe['command']);argv[argv.index('-o')+1]=str(binary)
 else:argv=['go','build','-trimpath','-buildvcs=false']+(['-overlay='+str(overlay)] if rep else[])+['-o',str(binary),pkg]
 start=time.monotonic()
 with (p/(name+'.build.stdout')).open('w') as out,(p/(name+'.build.stderr')).open('w') as err:result=subprocess.run(argv,cwd=r,env=env,stdout=out,stderr=err)
 commands.append({'argv':argv,'cwd':str(r),'explicit_env':{'GOOS':'linux','GOARCH':'amd64','CGO_ENABLED':'0'},'exit':result.returncode,'elapsed_seconds':time.monotonic()-start});assert result.returncode==0,argv
 sha=hashf(binary);assert expected is None or sha==expected,(name,sha,expected)
 info=subprocess.check_output(['go','version','-m',str(binary)],cwd=r,text=True);(p/(name+'.buildinfo.txt')).write_text(info)
 artifacts.append({'path':str(binary),'sha256':sha,'bytes':binary.stat().st_size,'expected_historical_or_current_sha256':expected,'actual_byte_identical_to_expected':sha==expected if expected else None,'buildinfo_sha256':hashf(p/(name+'.buildinfo.txt'))})
after={name:binding(pkg,rep) for name,pkg,rep,_ in plans};assert before==after
(p/'compile-inputs-after.json').write_text(json.dumps(after,indent=2)+'\n')
# SHA256 and Git object identities bind actual working inputs; do not pretend a
# dirty Manifest is identical to HEAD merely because buildvcs=false was used.
git=[]
for f in [source,r/'plugins/mpserverstatus/plugin.go',probe,r/'internal/sdk/protocol.go',r/'SDK_ORIGIN.json',r/'go.mod',r/'go.sum',update]:
 actual_blob=subprocess.check_output(['git','hash-object',str(f)],cwd=r,text=True).strip()
 try:rel=str(f.relative_to(r));head_blob=subprocess.check_output(['git','rev-parse','HEAD:'+rel],cwd=r,text=True,stderr=subprocess.DEVNULL).strip()
 except subprocess.CalledProcessError:head_blob=None
 git.append({'path':str(f),'sha256':hashf(f),'working_content_git_blob':actual_blob,'HEAD_blob':head_blob,'working_matches_HEAD':actual_blob==head_blob if head_blob else None})
(p/'git-source-binding.json').write_text(json.dumps({'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=r,text=True).strip(),'files':git,'note':'Current declaration edits may differ from HEAD. Per-file content/blob and before/after compile input bindings are authoritative; buildinfo alone is not source provenance.'},indent=2)+'\n')
(p/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');(p/'artifacts.json').write_text(json.dumps(artifacts,indent=2)+'\n');(p/'toolchain.json').write_text(subprocess.check_output(['go','env','-json','GOVERSION','GOOS','GOARCH','CGO_ENABLED','GOFLAGS','GOTOOLCHAIN'],cwd=r,text=True))
legacy={'wrapper':{'path':str(r/'work/migration-20261105/pluginuninstall-main-runtime-20261106/run_owned_main.py'),'sha256':hashf(r/'work/migration-20261105/pluginuninstall-main-runtime-20261106/run_owned_main.py')},'input_inventory':{'path':str(r/'work/migration-20261105/pluginuninstall-main-runtime-20261106/input-inventory.json'),'sha256':hashf(r/'work/migration-20261105/pluginuninstall-main-runtime-20261106/input-inventory.json')},'driver_freeze':{'path':str(old/'freeze.json'),'sha256':hashf(old/'freeze.json')},'source':{'path':str(probe),'sha256':hashf(probe)},'old_actual_probe_sha256':'b4d23deb2ba9d58dbd30dc56d6f212c5498cad35272160716dc0c85650ec7744','new_exact_same_source_command_except_output_path':True}
(p/'legacy-probe-binding.json').write_text(json.dumps(legacy,indent=2)+'\n')
(p/'verification.json').write_text(json.dumps({'scope':'local preparation only; no NAS/Main/UI/runtime/DB access','compile_inputs_before_after_identical':True,'per_artifact_local_module_inputs':{k:len(v) for k,v in before.items()},'PUI_base_rebuild_equals_current_d001':True,'MPS_rebuild_equals_current_3278':True,'probe_rebuild_equals_actual_old_Main1_b4d':True,'update_only_difference':'Version 2.2 to 2.2.1 in complete current plugins/pluginuninstall/plugin.go overlay','SDK98_sha256':sdk_expected,'retained_temporary_ELFs':4,'actual_Main2_executed':False},indent=2)+'\n')
print(json.dumps(artifacts,indent=2))
