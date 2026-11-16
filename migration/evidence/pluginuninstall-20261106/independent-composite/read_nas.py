from pathlib import Path
import subprocess,json,hashlib
out=Path(__file__).resolve().parent
payload=r'''
from pathlib import Path
import os,json,hashlib,sqlite3
root=Path('/home/admin/light-media-plugins-migration-pluginuninstall-20261105');assert os.getuid()==1000
assert (root/'.task-owned').read_text().strip()=='light-media-plugins/PluginUnInstall/20261105/owned-only'
runtime=root/'main-run-1/runtime';assert (runtime/'.task-owned').read_text()=='light-media-plugins/PluginUnInstall/20261105/owned-only'
paths={'PUI':root/'bin/plugin-uninstall-linux','update':root/'bin/plugin-uninstall-2.2.1-linux','fixture':root/'bin/owned-pui-fixture-linux','driver':root/'bin/pluginuninstall-main-linux.test','host':Path('/home/admin/light-media-plugins-migration-sdk98-20261105/bin/light-media-host-pluginuninstall-reviewed-linux'),'MPS':Path('/home/admin/light-media-plugins-migration-sdk98-20261105/bin/mp-server-status-linux-amd64')}
report={'classification':'read-only owned NAS UID1000 marker/binary/process/SQLite metadata sample; no credential decryption/HTTP/reexecution','bins':{},'runtime':str(runtime),'processes':[]}
for role,p in paths.items():assert p.is_file() and not p.is_symlink();b=p.read_bytes();report['bins'][role]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  exe=os.readlink(p/'exe');cmd=(p/'cmdline').read_bytes()
 except (FileNotFoundError,PermissionError,OSError):continue
 if exe.startswith(str(runtime/'plugin-packages')) or (b'--data-dir\0'+str(runtime).encode()+b'\0') in cmd:report['processes'].append({'pid':int(p.name),'executable_basename':Path(exe).name})
con=sqlite3.connect('file:'+str(runtime/'light-media.db')+'?mode=ro',uri=True)
report['installations']=[dict(zip(['instance_id','plugin_id','version','installed'],row)) for row in con.execute('SELECT instance_id,plugin_id,version,installed FROM plugin_installations ORDER BY instance_id')]
report['value_metadata']=[{'instance_id':id,'kind':kind,'item_key':key,'revision':rev,'ciphertext_bytes':len(sealed),'ciphertext_sha256':hashlib.sha256(sealed).hexdigest()} for id,kind,key,rev,sealed in con.execute('SELECT instance_id,kind,item_key,revision,sealed FROM plugin_values ORDER BY instance_id,kind,item_key')]
con.close();report['plain_own_marker_count']=sum(p.is_file() for p in runtime.rglob('owned-plain-marker'))
assert report['processes']==[]
print(json.dumps(report))
'''
(out/'nas-readonly-payload.py').write_text(payload)
cmd=['ssh','admin@192.168.8.129','python3','-'];r=subprocess.run(cmd,input=payload.encode(),capture_output=True)
(out/'nas-readonly.json').write_bytes(r.stdout);(out/'nas-readonly.stderr').write_bytes(r.stderr);(out/'nas-readonly-command.json').write_text(json.dumps({'command':cmd,'exit':r.returncode,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest()},indent=2)+'\n')
print('exit',r.returncode,'bytes',len(r.stdout))
if r.returncode:print(r.stderr.decode())
