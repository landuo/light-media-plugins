from pathlib import Path
import ast,json,subprocess,uuid,hashlib
r=Path('/Users/accidia/projects/light-media-plugins');w=r/'work/sites-review-20261105/pluginuninstall-review';p=r/'work/sites-review-20261105/pluginuninstall-source-only/startup-reinit-addon/execution-payload-r3.py';a=ast.parse(p.read_bytes());a.body=[n for n in a.body if n.lineno<201];payload=ast.unparse(a)+'''
with tempfile.TemporaryDirectory(prefix='independent-empty-stat-') as tmp:
 denied=pathlib.Path(tmp)/'denied';(denied/'app/plugins').mkdir(parents=True);ns['settings']=SimpleNamespace(ROOT_PATH=denied);denied.chmod(0)
 error=None;result=None
 try:
  try:result=Manager._load_selective_plugins(None,[],lambda m:True)
  except BaseException as e:error={'class':type(e).__name__,'errno':getattr(e,'errno',None)}
 finally:denied.chmod(0o700)
 print(json.dumps({'runtime':sys.version,'source_manager_sha256':hashlib.sha256(SOURCES['manager'].encode()).hexdigest(),'classification':'actual original selective-loader AST, real UID65534 owned tmpfs search-denied ancestor; empty installed membership; no app imports/config/DB/network','empty_installed':[],'result':result,'error':error}))
''';(w/'empty-stat-source-payload.py').write_text(payload);label='lm-independent-pui-empty-'+uuid.uuid4().hex;cmd=['ssh','admin@192.168.8.129','docker run --rm -i --label task='+label+' --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -'];b=subprocess.run(cmd,input=payload.encode(),capture_output=True);(w/'empty-stat-source-oracle.json').write_bytes(b.stdout);(w/'empty-stat-source-stderr.txt').write_bytes(b.stderr);check=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(check,capture_output=True);(w/'empty-stat-source-command.json').write_text(json.dumps({'command':cmd,'exit':b.returncode,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest(),'cleanup_command':check,'cleanup_exit':c.returncode,'remaining_containers':c.stdout.decode()},indent=2)+'\n');print(json.dumps({'exit':b.returncode,'bytes':len(b.stdout),'remaining':c.stdout.decode()}))
if b.returncode:print(b.stderr.decode());raise SystemExit(b.returncode)
