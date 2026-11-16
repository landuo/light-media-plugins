from pathlib import Path
import os,json,hashlib,subprocess,shutil,datetime
r=Path('/home/admin/light-media-plugins-migration-mps-20261105');shared=Path('/home/admin/light-media-plugins-migration-sdk98-20261105');assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/MPServerStatus/20261105/owned-only';assert (shared/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
processes=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes()
 except (OSError,PermissionError):continue
 if str(r).encode() in cmd:processes.append(int(p.name))
assert not processes,processes
assert not subprocess.check_output(['docker','ps','-a','--filter','label=task=light-media-plugins.MPServerStatus.20261105','--format','{{.ID}}'],text=True).strip()
net=json.loads(subprocess.check_output(['docker','network','inspect','lm-plugins-mps-internal-20261105']))[0];assert net['Id']=='d25278677c0149f5f3a4cab20cd52743c8754c3bf7f6f35dfd66e36c7cd4c852' and net['Labels']=={'task':'light-media-plugins.MPServerStatus.20261105'} and not net['Containers'] and net['Internal']
source=r/'bin/mp-server-status-linux-amd64';dest=shared/'bin/mp-server-status-linux-amd64';expected='66300eecf0ce7d785e3a448c338e163cfa83ac43cb13bce3e4efaeebfe852055';assert not source.is_symlink() and hashlib.sha256(source.read_bytes()).hexdigest()==expected and not dest.exists();source.rename(dest)
counts={'files':0,'bytes':0}
for p in r.rglob('*'):
 if p.is_file() and not p.is_symlink():counts['files']+=1;counts['bytes']+=p.stat().st_size
subprocess.run(['docker','network','rm',net['Id']],check=True,stdout=subprocess.PIPE);shutil.rmtree(r)
print(json.dumps({'classification':'owned test runtime cleanup after sealed readonly sample and public-safe evidence harvest; source production service untouched','utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'uid':os.getuid(),'marker_verified':True,'owned_processes':processes,'owned_containers':[],'removed_network_id':net['Id'],'removed_runtime':str(r),'root_absent':not r.exists(),'removed_payload':counts,'retained_shared_input':{'path':str(dest),'sha256':expected,'reason':'single current MPS worker for subsequent PluginUnInstall host tests'},'no_global_CA_hosts_SSH_config_changes':True}))
