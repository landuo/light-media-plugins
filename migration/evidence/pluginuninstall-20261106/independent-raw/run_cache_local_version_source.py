from pathlib import Path
import ast,json,subprocess,uuid,hashlib
r=Path('/Users/accidia/projects/light-media-plugins');w=r/'work/sites-review-20261105/pluginuninstall-review';original=r/'work/sites-review-20261105/pluginuninstall-source-only/startup-reinit-addon/execution-payload-r3.py';tree=ast.parse(original.read_bytes());tree.body=[n for n in tree.body if n.lineno<201]
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run_case')
class Inject(ast.NodeTransformer):
 def visit_Assign(self,n):
  if isinstance(n.value,ast.Name) and n.value.id=='fault_name' and any(isinstance(t,ast.Name) and t.id=='fault' for t in n.targets):return [n,ast.Assign(targets=[ast.Name(id='fail',ctx=ast.Store())],value=ast.Name(id='fault_name',ctx=ast.Load()))]
  return n
Inject().visit(fn);ast.fix_missing_locations(tree)
payload=ast.unparse(tree)+'''
node=next(n for c in ast.parse(SOURCES['manager']).body if isinstance(c,ast.ClassDef) and c.name=='PluginManager' for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='get_local_plugin_version')
exec(compile(ast.Module(body=[node],type_ignores=[]),'manager','exec',flags=__future__.annotations.compiler_flag),ns);Manager.get_local_plugin_version=ns['get_local_plugin_version']
result=run_case('cold-future99-installed-db-failure','cold',['MPServerStatus'],installed=['PluginUnInstall','MPServerStatus'],fault_name='db:UserInstalledPlugins')
result['actual_version_getter_after']=m.get_local_plugin_version('MPServerStatus')
print(json.dumps({'runtime':sys.version,'classification':'actual original Manager.start/get_local_plugins + PUI + SystemConfigOper.set AST; synthetic SQL Row.update raises after source cache copy; real owned tmpfs code removal; no production sourceimport/config/DB/network','source_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in SOURCES.items()},'case':result},ensure_ascii=False))
''';(w/'cache-local-version-source-payload.py').write_text(payload);label='lm-independent-pui-cache-'+uuid.uuid4().hex;cmd=['ssh','admin@192.168.8.129','docker run --rm -i --label task='+label+' --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=64m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -'];a=subprocess.run(cmd,input=payload.encode(),capture_output=True);(w/'cache-local-version-source-oracle.json').write_bytes(a.stdout);(w/'cache-local-version-source-stderr.txt').write_bytes(a.stderr);check=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(check,capture_output=True);(w/'cache-local-version-source-command.json').write_text(json.dumps({'command':cmd,'exit':a.returncode,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest(),'original_harness_sha256':hashlib.sha256(original.read_bytes()).hexdigest(),'cleanup_command':check,'cleanup_exit':c.returncode,'remaining_containers':c.stdout.decode()},indent=2)+'\n');print(json.dumps({'exit':a.returncode,'bytes':len(a.stdout),'remaining':c.stdout.decode()}))
if a.returncode:print(a.stderr.decode());raise SystemExit(a.returncode)
