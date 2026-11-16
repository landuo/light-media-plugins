from pathlib import Path
import json,os,hashlib,shutil,socket,platform
root=Path('/home/admin/light-media-plugins-migration-category-20261105-actualmain')
expected={'light-media-host-linux': '0162d7edd2c22af31b2adf6348c224304d020c5800551605d9e172b9c525cce5', 'category-editor-linux': '091493585e9a33b68ddc1ea3e11e5b2fccacb16289b7284771c7862bc5e33cd3', 'category-editor-update-linux': 'f46fef8bbcc8c18ed8c5b3fb7c28196e793842bb81628d502bec3005646b02df', 'categoryeditor-main-linux.test': '26f559bc85e59bc6b61e0a5b8f54c16b0f6389f2064bb36d69cdee671d1a2c07'}
assert root.is_dir() and not root.is_symlink()
marker=json.loads((root/'.task-owned.json').read_text())
assert marker['task']=='installed-plugin-migration-20261105-CategoryEditor-actual-main' and marker['root']==str(root)
assert {p.name for p in root.iterdir()}=={'.task-owned.json','bin','bundled-source-category.yaml','run','run.log'}
actual={name:hashlib.sha256((root/'bin'/name).read_bytes()).hexdigest() for name in expected}
assert actual==expected,'transferred executable bytes differ'
pids=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   exe=os.readlink(p/'exe')
   if exe.startswith(str(root)+'/'):pids.append({'pid':int(p.name),'exe':exe})
  except (FileNotFoundError,PermissionError,ProcessLookupError):pass
assert not pids,pids
s=socket.socket();port_result=s.connect_ex(('127.0.0.1',36251));s.close();assert port_result!=0,'owned test port still listening'
policy=root/'run/category.yaml';raw=policy.read_bytes();before=json.loads((root/'run/evidence/ui-final-http.json').read_text())
assert hashlib.sha256(raw).hexdigest()==before['global_policy_sha256']
assert policy.stat().st_ino==before['inode'] and policy.stat().st_mtime_ns==before['mtime_ns']
assert not (root/'run/plugin-packages/CategoryEditorowned').exists()
assert (root/'run/plugin-packages/CategoryEditor/category-editor').is_file()
record={'root':str(root),'host_environment':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),'uid':os.getuid()},'executable_sha256':actual,'running_owned_processes':pids,'owned_port_closed':True,'final_policy':{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'same_inode_as_UI':True,'same_mtime_ns_as_UI':True,'mode':oct(policy.stat().st_mode&0o777)},'clone_package_removed':True,'source_package_reinstalled':True,'root_marker_validated':True}
shutil.rmtree(root)
assert not root.exists()
record['owned_remote_directory_removed']=True
print(json.dumps(record,ensure_ascii=False,indent=2))
