from pathlib import Path
import ast,subprocess,json,hashlib,uuid
P=Path('/Users/accidia/projects/light-media-plugins');W=P/'work/sites-review-20261106/current-consumer-main-review/custom-scrap-source312';W.mkdir(exist_ok=True);source=(P/'work/migration-20261105/source-snapshot/removelink/__init__.py').read_text();sourcehash=hashlib.sha256(source.encode()).hexdigest()
payload='''import ast,sys,json,tempfile,shutil,os,types,hashlib
from pathlib import Path
s=SOURCE
assert hashlib.sha256(s.encode()).hexdigest()==EXPECTED
tr=ast.parse(s);klass=next(x for x in tr.body if isinstance(x,ast.ClassDef)and x.name=='RemoveLink');names={'_parse_custom_scrap_extensions','_scrap_extensions','_is_scrap_file','delete_scrap_infos'}
constants=[]
for n in klass.body:
 if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name)and t.id in ['SCRAP_EXTENSIONS','SCRAP_DIR_SUFFIXES']for t in n.targets):constants.append(n)
body=constants+[n for n in klass.body if isinstance(n,ast.FunctionDef)and n.name in names]
new=ast.ClassDef(name='ObservedSource',bases=[],keywords=[],body=body,decorator_list=[]);f=next(n for n in tr.body if isinstance(n,ast.FunctionDef)and n.name=='is_trickplay_path');tree=ast.fix_missing_locations(ast.Module(body=[f,new],type_ignores=[]));logs=[];env={'Path':Path,'List':list,'os':os,'shutil':shutil,'logger':types.SimpleNamespace(info=lambda m:logs.append(['info',m]),error=lambda m:logs.append(['error',m]))};exec(compile(tree,'installed-removelink-exact-selected-methods','exec'),env)
with tempfile.TemporaryDirectory(prefix='owned-source-scrap-')as td:
 root=Path(td);o=env['ObservedSource']();o._delete_scrap_infos=True;o._custom_scrap_extensions=o._parse_custom_scrap_extensions('OWN，-mediainfo.JSON');o.delete_empty_folders=lambda p:None
 removed=['OwnedFilm.1080p.nfo','OwnedFilm.1080p.OWN','OwnedFilm.1080p-mediainfo.JSON','OwnedFilm.1080p.trickplay'];kept=['OwnedFilm.nfo','Other.OWN','Other.trickplay','keep.bin']
 for name in removed+kept:
  p=root/name
  if name.endswith('.trickplay'):(p/'nested').mkdir(parents=True);(p/'nested/frame.bin').write_bytes(b'owned')
  else:p.write_bytes(b'owned')
 o.delete_scrap_infos(root/'OwnedFilm.1080p.mkv')
 out={'classification':'actual original method AST+stdlib filesystem only; no app import/config/DB; synthetic no-op parent-empty helper isolates related scraper selection, other full-flow/empty logic separately proved','runtime':sys.version,'source_sha256':EXPECTED,'custom':o._custom_scrap_extensions,'removed':[n for n in removed if not(root/n).exists()],'retained':[n for n in kept if(root/n).exists()],'errors':[m for k,m in logs if k=='error'],'logs':[[k,m.replace(td,'@ROOT@')]for k,m in logs],'app_modules_imported':[n for n in sys.modules if n=='app'or n.startswith('app.')]};print(json.dumps(out,ensure_ascii=False));assert len(out['removed'])==4 and len(out['retained'])==4 and not out['errors']and not out['app_modules_imported']
'''.replace('SOURCE',repr(source),1).replace('EXPECTED',repr(sourcehash));(W/'payload.py').write_text(payload)
label='lm-independent-custom-scrap-'+uuid.uuid4().hex;cmd=['ssh','admin@192.168.8.129','docker run --rm -i --label task='+label+' --network none --read-only --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --tmpfs /tmp:rw,nosuid,nodev,noexec,size=32m,mode=1777 --entrypoint python sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881 -B -S -'];r=subprocess.run(cmd,input=payload.encode(),capture_output=True);(W/'source.stdout').write_bytes(r.stdout);(W/'source.stderr').write_bytes(r.stderr);cleanup=['ssh','admin@192.168.8.129','docker ps -aq --filter label=task='+label];c=subprocess.run(cleanup,capture_output=True);(W/'source-command.json').write_text(json.dumps({'argv':cmd,'exit':r.returncode,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest(),'cleanup_argv':cleanup,'cleanup_exit':c.returncode,'containers_remaining':c.stdout.decode()},indent=2));assert r.returncode==0,r.stderr.decode();assert c.returncode==0 and not c.stdout.strip();(W/'source-oracle.json').write_text(json.dumps(json.loads(r.stdout),indent=2,ensure_ascii=False)+'\n');print(hashlib.sha256((W/'source-oracle.json').read_bytes()).hexdigest())
