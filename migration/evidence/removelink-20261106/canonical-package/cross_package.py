from pathlib import Path
import importlib.util, subprocess, json, hashlib, os, tempfile, zipfile, sys, datetime

root=Path.cwd();out=Path(__file__).resolve().parent
expected=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
peer='admin@192.168.8.129';remote='/home/admin/light-media-plugins-migration-removelink-20261105'
spec=importlib.util.spec_from_file_location('canonical_builder',root/'scripts/build_plugins.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
sha=lambda b:hashlib.sha256(b).hexdigest()
entry={'id':'RemoveLink','package':'./cmd/remove-link','host_contract':'light-media.sdk-resources/v1','license_files':['LICENSE.upstream','THIRD_PARTY_NOTICES.md','third_party/Go-LICENSE','third_party/x-text-LICENSE','third_party/x-text-PATENTS'],'frontend':{'command':['cp','-R','plugins/removelink/frontend','{output}'],'cwd':'.','output':'frontend-output'}}
(out/'candidate-build-config.json').write_text(json.dumps({'plugins':[entry]},indent=2)+'\n')
builder.read_config(out/'candidate-build-config.json')
before={str(p.relative_to(root)):sha(p.read_bytes())for p in [root/'scripts/build_plugins.py',root/'go.mod',root/'go.sum',root/'SDK_ORIGIN.json',*sorted((root/'plugins/removelink/frontend').iterdir())] if p.is_file()}
original_command=builder.command;native_commands=[]
def ssh(code):
 p=subprocess.run(['ssh',peer,'python3','-'],input=code.encode(),capture_output=True)
 assert p.returncode==0,p.stderr.decode()
 return p.stdout
def command(argv,cwd,env,timeout=600):
 if len(argv)==2 and argv[1]=='--manifest' and Path(argv[0]).name=='compiled-worker':
  worker=Path(argv[0]);assert sha(worker.read_bytes())==expected,'canonical worker differs from producer freeze'
  prefix="from pathlib import Path\nimport os,hashlib,subprocess\nr=Path("+repr(remote)+")\nassert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'\nd=r/'package-manifest-owned'\n"
  ssh(prefix+"assert not d.exists()\nd.mkdir(mode=0o700)\n")
  try:
   subprocess.run(['scp',str(worker),peer+':'+remote+'/package-manifest-owned/compiled-worker'],capture_output=True,check=True)
   actual=ssh(prefix+"p=d/'compiled-worker'\nassert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()=="+repr(expected)+"\np.chmod(0o755)\np=subprocess.run([str(p),'--manifest'],capture_output=True,timeout=30)\nassert p.returncode==0\nos.write(1,p.stdout)\n")
   (out/'actual-linux-manifest.json').write_bytes(actual);native_commands.append({'command':['compiled-worker','--manifest'],'worker_sha256':expected,'manifest_sha256':sha(actual),'actual_UID':1000,'actual_platform':'Linux/amd64'})
   return actual
  finally:
   ssh(prefix+"p=d/'compiled-worker'\nassert not p.is_symlink()\np.unlink(missing_ok=True)\nd.rmdir()\n")
 return original_command(argv,cwd,env,timeout)
builder.command=command
output=builder.fresh_output(out/'canonical-output');base=builder.release_base('https://example.invalid/not-published/removelink-20261106')
with tempfile.TemporaryDirectory(prefix='.canonical-removelink-',dir=out) as td:
 build=Path(td);index,archive=builder.build_plugin(root,build,entry,base,'go')
 artifact=index['releases'][0]['artifacts'][0];assert artifact['executable_sha256']==expected and len(artifact['files'])==10
 notices=build/'THIRD_PARTY_LICENSES.zip';builder.archive_plugin(notices,builder.license_inventory(root,[entry]))
 builder.publish_fresh(output,[archive,notices],{'schema_version':1,'plugins':[index]})
 with zipfile.ZipFile(output/archive.name) as zipped:
  assert zipped.testzip() is None and len(zipped.namelist())==10
  for item in artifact['files']:
   data=zipped.read(item['path']);assert len(data)==item['size'] and sha(data)==item['sha256']
  for name in ['remoteEntry.js','view.js','style.css']:assert zipped.read('frontend/'+name)==(root/'plugins/removelink/frontend'/name).read_bytes()
after={name:sha((root/name).read_bytes())for name in before};assert before==after
result={'classification':'actual canonical build_plugin/build_frontend/archive/publish_fresh functions with actual cross-built Linux ELF and native owned NAS manifest; no CLI platform spoof or Python product runtime; candidate config only, not registry acceptance or remote release','exit_code':0,'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'worker_sha256':expected,'build_script_sha256':before['scripts/build_plugins.py'],'source_before':before,'source_after':after,'source_stable':before==after,'native_commands':native_commands,'plugin_spec':entry,'artifacts':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())}for p in sorted(output.iterdir())],'member_inventory':artifact['files'],'native_manifest_scratch_removed':True}
(out/'canonical-package-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'exit_code':0,'worker_sha256':expected,'package_members':10,'artifacts':len(result['artifacts'])}))
