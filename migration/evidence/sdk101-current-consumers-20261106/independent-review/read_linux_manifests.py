from pathlib import Path
import json,subprocess,time,hashlib
r=Path('/Users/accidia/projects/light-media-plugins');w=Path(__file__).resolve().parent;builds=json.loads((r/'work/parallel-sdk-sync-20261106/linux-consumer-builds.json').read_text());expected=[]
for row in builds:
 root='/home/admin/light-media-plugins-migration-removelink-20261105'if row['id'].startswith('RemoveLink')else'/home/admin/light-media-plugins-migration-sdk98-20261105'
 expected.append({'id':row['id'],'path':root+'/bin/sdk101-'+row['id']+'-linux','sha256':row['sha256']})
payload='EXPECTED='+repr(expected)+'\n'+r'''
import os,pathlib,hashlib,json,subprocess
assert os.getuid()==1000
for root,marker in [('/home/admin/light-media-plugins-migration-removelink-20261105','light-media-plugins/RemoveLink/20261105/owned-only'),('/home/admin/light-media-plugins-migration-sdk98-20261105','light-media-plugins/SDK98/20261105/owned-only')]:
 assert(pathlib.Path(root)/'.task-owned').read_text().strip()==marker
rows=[]
for item in EXPECTED:
 p=pathlib.Path(item['path']);assert p.is_file()and not p.is_symlink();before=hashlib.sha256(p.read_bytes()).hexdigest();assert before==item['sha256']
 q=subprocess.run([str(p),'--manifest'],capture_output=True,timeout=5)
 after=hashlib.sha256(p.read_bytes()).hexdigest();assert after==before
 rows.append(dict(item,exit=q.returncode,stdout=q.stdout.decode(),stderr=q.stderr.decode(),unchanged=after==before))
print(json.dumps({'classification':'independent actual NAS UID1000 eight exact currentSDK101 --manifest entries only; no init/network/host/App execution or runtime writes','rows':rows},indent=2))
'''
(w/'linux-manifest-payload.py').write_text(payload);argv=['ssh','admin@192.168.8.129','python3','-'];start=time.monotonic();p=subprocess.run(argv,input=payload.encode(),capture_output=True,timeout=55);(w/'linux-manifests.json').write_bytes(p.stdout);(w/'linux-manifests.stderr').write_bytes(p.stderr);(w/'linux-manifests-command.json').write_text(json.dumps({'argv':argv,'exit':p.returncode,'seconds':time.monotonic()-start,'stdin_sha256':hashlib.sha256(payload.encode()).hexdigest(),'files_created_on_NAS':[],'readonly_arguments':['--manifest']},indent=2)+'\n');assert p.returncode==0,p.stderr.decode();x=json.loads(p.stdout);print([(z['id'],z['exit'],json.loads(z['stdout'])['plugin_id'],json.loads(z['stdout'])['version'])for z in x['rows']])
