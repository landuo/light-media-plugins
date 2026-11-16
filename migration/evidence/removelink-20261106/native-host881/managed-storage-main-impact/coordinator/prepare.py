from pathlib import Path
import subprocess,json,hashlib
root=Path.cwd();out=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
binary=Path('/Users/accidia/projects/light-media/work/shared-host-managed-storage-20261106/light-media-host-managed-storage-linux');expected='6ce69c24f883dba3ab45b9e51bc0262934f3372c454533e119667c5791ea6db1';assert sha(binary)==expected
shared=Path('/home/admin/light-media-plugins-migration-sdk98-20261105');rlk=Path('/home/admin/light-media-plugins-migration-removelink-20261105');remote=shared/'bin/light-media-host-managed-storage-linux'
check=f"from pathlib import Path\nimport os\nr=Path({str(shared)!r});assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'\np=Path({str(remote)!r});assert p.parent.is_dir() and not p.parent.is_symlink() and not p.exists() and not p.is_symlink()\n"
subprocess.run(['ssh','admin@192.168.8.129','python3','-'],input=check.encode(),check=True)
subprocess.run(['scp',str(binary),'admin@192.168.8.129:'+str(remote)],check=True)
inputs=json.loads((root/'work/migration-20261105/removelink-main7-20261106/input-inventory-run7.json').read_text());inputs.pop(str(shared/'bin/light-media-host-getter-gates-linux'));inputs[str(remote)]=expected
(out/'input-inventory-run8.json').write_text(json.dumps(inputs,indent=2)+'\n')
subprocess.run(['scp',str(out/'input-inventory-run8.json'),'admin@192.168.8.129:'+str(rlk/'input-inventory-run8.json')],check=True)
s=(root/'work/migration-20261105/removelink-main7-20261106/run_owned_main.py').read_text().replace('input-inventory-run7.json','input-inventory-run8.json').replace('main-run-7','main-run-8').replace('light-media-host-getter-gates-linux','light-media-host-managed-storage-linux').replace('3c0513c3c92e4ab15128f1d0c0756cdd4c763403d0dc2b6111f8812a36d1c6cb',expected).replace("REMOVELINK_LISTEN='0.0.0.0:36256',REMOVELINK_PUBLIC_URL='http://192.168.8.129:36256',REMOVELINK_UI_WAIT='1'","REMOVELINK_LISTEN='127.0.0.1:36256',REMOVELINK_UI_WAIT='0'")
s=s.replace('actual native UID1000 ordinary Go Main3a3f+4optional-getter source fixes','actual native UID1000 ordinary Go Main651dd+2managed-storage source fixes; no new browser run')
s=s.replace("'minimum_host_commit':'651dd2c3f75f4be74951d0a552f93a9079046e1d'","'base_host_commit':'651dd2c3f75f4be74951d0a552f93a9079046e1d','new_host_source_binding':'/Users/accidia/projects/light-media/work/shared-host-managed-storage-20261106/build-source-binding.json','new_host_status':'local candidate651dd+2source fixes; independent review and actualMain gates pending; no invented committed revision'")
s=s.replace("'prepared_local_binding_sha256':'68bfe6bc5473b719132adafa1da981d27cf287e818c3e1ecd04549852da6b097'","'historical_Main7_prepared_binding_sha256':'68bfe6bc5473b719132adafa1da981d27cf287e818c3e1ecd04549852da6b097','current_prepared_source':'managed-storage-main-impact/input-inventory-run8.json'")
(out/'run_main8.py').write_text(s)
print(json.dumps({'prepared_host_sha256':expected,'inputs':len(inputs),'run':'main-run-8','actual_main_executed':False}))
