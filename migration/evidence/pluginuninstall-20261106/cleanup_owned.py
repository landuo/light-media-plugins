from pathlib import Path
import json,hashlib,subprocess,datetime
root=Path.cwd();own=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
payload=r'''
from pathlib import Path
import os,json,hashlib,shutil,datetime
r=Path('/home/admin/light-media-plugins-migration-pluginuninstall-20261105');s=Path('/home/admin/light-media-plugins-migration-sdk98-20261105')
assert os.getuid()==1000 and (r/'.task-owned').read_text()=='light-media-plugins/PluginUnInstall/20261105/owned-only'
assert (s/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
for child in ['main-run-1/runtime','package-main-1/runtime']:assert (r/child/'.task-owned').read_text()=='light-media-plugins/PluginUnInstall/20261105/owned-only'
assert (s/'main-run-5/.task-owned').read_text().strip()=='light-media-plugins/SDK98Impact/20261105/owned-only'
found=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (OSError,PermissionError):continue
 if str(r).encode() in cmd or str(s).encode() in cmd:found.append(int(p.name))
assert not found,found
retained=r/'bin/plugin-uninstall-linux';dest=s/'bin/plugin-uninstall-sdk98-linux-amd64';h=hashlib.sha256(retained.read_bytes()).hexdigest();assert h=='86cf644722a7bace3b8f860426c86d044e5c9d9659586160f737c76e58fb2df1' and not dest.exists();retained.rename(dest)
assert not (r/'main-run-1/runtime/ui-ready.private.json').exists()
counts={str(q):sum(1 for p in q.rglob('*')if p.is_file()) for q in [r,s/'main-run-5']}
shutil.rmtree(r);shutil.rmtree(s/'main-run-5')
print(json.dumps({'classification':'marker-verified complete owned PUI synthetic runtime/bin cleanup plus completed SDK impact run5; all source/main/package/UI/DB facts already independently sampled and raw evidence preserved; no production paths or global services touched','uid':os.getuid(),'matching_processes_before':found,'removed_roots':[{ 'path':str(q),'files_before':counts[str(q)],'absent_after':not q.exists()}for q in [r,s/'main-run-5']],'retained_single_next_acceptance_input':{'path':str(dest),'sha256':h},'at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}))
'''
p=subprocess.run(['ssh','admin@192.168.8.129','python3','-'],input=payload.encode(),capture_output=True)
(own/'cleanup-nas.stdout').write_bytes(p.stdout);(own/'cleanup-nas.stderr').write_bytes(p.stderr);assert p.returncode==0,p.stderr.decode();remote=json.loads(p.stdout)
shared=root/'work/migration-20261105/shared-acceptance-inputs';shared.mkdir(exist_ok=True)
moves=[]
for src,name,h in [(root/'work/migration-20261105/pluginuninstall-20261105/plugin-uninstall-linux','plugin-uninstall-sdk98-linux-amd64','86cf644722a7bace3b8f860426c86d044e5c9d9659586160f737c76e58fb2df1'),(root/'work/migration-20261105/pluginuninstall-20261105/mp-server-status','mp-server-status-sdk98-native-arm64','66d046374934df41d6935ed69a7192e9110f279c78a34b4b68baeca4669f087b')]:
 assert src.is_file() and not src.is_symlink() and sha(src)==h
 dest=shared/name;assert not dest.exists();src.rename(dest);moves.append({'from':str(src.relative_to(root)),'to':str(dest.relative_to(root)),'sha256':h,'reason':'single upcoming shared-SDK compatibility input retained; not duplicated'})
paths={}
for file in [root/'work/migration-20261105/pluginuninstall-20261105/verification.json',root/'work/migration-20261105/pluginuninstall-main-driver-20261105/freeze.json']:
 d=json.loads(file.read_text());art=d['artifacts'];records=art.values()if isinstance(art,dict)else art
 for f in records:
  q=Path(f['path']);paths[q]=f['sha256']
package=root/'work/migration-20261105/pluginuninstall-packaging-20261106'
for q in [package/'canonical-package-main-linux.test',package/'cross-output/PluginUnInstall-2.2-linux-amd64.zip']:
 paths[q]=sha(q)
deleted=[]
for q,h in paths.items():
 if not q.exists():continue
 assert q.is_relative_to(root/'work') and q.is_file() and not q.is_symlink() and sha(q)==h
 n=q.stat().st_size;q.unlink();deleted.append({'path':str(q.relative_to(root)),'sha256':h,'bytes':n,'absent_after':not q.exists()})
result={'classification':'completed PUI fixture cleanup after independent complete1c17; data/evidence source hashes retained; necessary single next-SDK test inputs preserved','remote':remote,'local_single_input_moves':moves,'owned_local_generated_artifacts_removed':deleted,'remote_or_production_delivery':False}
(own/'owned-runtime-cleanup.json').write_text(json.dumps(result,indent=2)+'\n');out=root/'migration/evidence/pluginuninstall-20261106/owned-runtime-cleanup.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'remote_roots_removed':len(remote['removed_roots']),'local_artifacts_removed':len(deleted),'single_inputs_retained':len(moves),'cleanup_sha256':sha(out)}))
