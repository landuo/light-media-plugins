import pathlib,json,subprocess,hashlib,tarfile,io,time
r=pathlib.Path('/Users/accidia/projects/light-media-plugins');p=r/'work/migration-20261106/source-module-manifest';a=json.loads((p/'artifacts.json').read_text());remote='/home/admin/light-media-plugins-migration-source-interfaces-20261106';task='lm-plugin-source-interfaces-20261106';image='sha256:33354456e8e19c65193b9ca471e45450a620c541759cc42e76cf00a03b025881'
items=[]
ids={'categoryeditor':'CategoryEditor','torrenttransfer':'TorrentTransfer','removelink':'RemoveLink','sitestatistic':'SiteStatistic','mpserverstatus':'MPServerStatus','pluginuninstall':'PluginUnInstall'}
for row in a:
 if row['target'] in ['linux','linux-update-only-version'] and row['family']!='test-driver':
  family=row['family'];instance=ids[family]+('.updatefixture' if row['target']=='linux-update-only-version' else '')
  items.append({'Family':family,'Instance':instance,'Binary':'/owned/'+pathlib.Path(row['path']).name})
  if family=='torrenttransfer':items.append({'Family':'torrenttransfermusic','Instance':'TorrentTransfermusic','Binary':'/owned/'+pathlib.Path(row['path']).name})
config={'Oracle':'/owned/source-oracle.json','Artifacts':items};(p/'linux-probe-input.json').write_text(json.dumps(config,indent=2)+'\n')
archive=io.BytesIO()
with tarfile.open(fileobj=archive,mode='w') as tf:
 for row in a:
  if row['target'] in ['linux','linux-update-only-version']:tf.add(row['path'],arcname=pathlib.Path(row['path']).name)
 tf.add(r/'tests/sourceinterfaces/testdata/source-oracle.json',arcname='source-oracle.json');tf.add(p/'linux-probe-input.json',arcname='probe.json')
payload=archive.getvalue();marker='task='+task+'\n'
setup=f'''import pathlib,sys,tarfile,io,os,json
p=pathlib.Path({remote!r})
if p.exists():
 assert (p/'TASK').read_text()=={marker!r} and sorted(x.name for x in p.iterdir())==['TASK'],'unexpected existing owned content; stop'
else:
 p.mkdir(mode=0o755);(p/'TASK').write_text({marker!r})
data=sys.stdin.buffer.read()
with tarfile.open(fileobj=io.BytesIO(data)) as tf:
 for m in tf.getmembers():
  assert m.isfile() and pathlib.PurePosixPath(m.name).name==m.name and not m.name.startswith('.'),'invalid owned tar member'
  target=p/m.name;target.write_bytes(tf.extractfile(m).read());target.chmod(m.mode&0o777)
print(json.dumps({{"created":str(p),"files":sorted(x.name for x in p.iterdir())}}))
'''
# Script travels as a quoted fixed command, archive through stdin only.
import shlex
cmd=['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3 -c '+shlex.quote(setup)]
start=time.monotonic();s=subprocess.run(cmd,input=payload,capture_output=True);(p/'linux-setup.stdout').write_bytes(s.stdout);(p/'linux-setup.stderr').write_bytes(s.stderr);assert s.returncode==0,s.stderr.decode(errors='replace')
run=f'''import pathlib,subprocess,json,sys,time
p=pathlib.Path({remote!r});assert (p/'TASK').read_text()=={marker!r}
command=['docker','run','--rm','--pull=never','--label','task={task}','--network=none','--read-only','--cap-drop=ALL','--security-opt=no-new-privileges','--user=1000:1000','--tmpfs','/tmp:rw,noexec,nosuid,nodev,size=16m','-v',str(p)+':/owned:ro','--entrypoint','/owned/source-interface-sdk-probe-linux',{image!r},'/owned/probe.json']
start=time.monotonic();r=subprocess.run(command,capture_output=True);sys.stdout.buffer.write(r.stdout);sys.stderr.buffer.write(r.stderr);(p/'run-meta.json').write_text(json.dumps({{"argv":command,"exit":r.returncode,"elapsed_seconds":time.monotonic()-start}}));sys.exit(r.returncode)
'''
cmd2=['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3 -c '+shlex.quote(run)]
s=subprocess.run(cmd2,capture_output=True);(p/'linux-sdk-results.json').write_bytes(s.stdout);(p/'linux-sdk.stderr').write_bytes(s.stderr)
# Always harvest real exit metadata and clean only exact marker-bound ownership.
cleanup=f'''import pathlib,subprocess,json,shutil
p=pathlib.Path({remote!r});assert (p/'TASK').read_text()=={marker!r}
meta=json.loads((p/'run-meta.json').read_text());ids=subprocess.check_output(['docker','ps','-aq','--filter','label=task={task}'],text=True).split();assert not ids,ids
files=sorted(x.name for x in p.iterdir());shutil.rmtree(p);print(json.dumps({{"run":meta,"container_ids_remaining":ids,"removed_exact_owned_root":str(p),"owned_root_exists_after":p.exists(),"removed_names":files}}))
'''
c=subprocess.run(['ssh','-o','BatchMode=yes','admin@192.168.8.129','python3 -c '+shlex.quote(cleanup)],capture_output=True);(p/'linux-cleanup.json').write_bytes(c.stdout);(p/'linux-cleanup.stderr').write_bytes(c.stderr)
(p/'linux-command.json').write_text(json.dumps({'image':image,'task_label':task,'owned_remote':remote,'ssh_auth':'existing authorized key/session; no secret args','setup_exit':0,'run_exit':s.returncode,'cleanup_exit':c.returncode,'elapsed_seconds':time.monotonic()-start,'tar_sha256':hashlib.sha256(payload).hexdigest(),'classification':'actual Linux GoSDK host+eight independent worker processes in fixed networknone/read-only/UID1000 image; no Python product/old app/config/DB/production network'},indent=2)+'\n')
assert s.returncode==0 and c.returncode==0,(s.returncode,c.returncode,s.stderr.decode(errors='replace'),c.stderr.decode(errors='replace'))
