from pathlib import Path
import os,json,hashlib,shutil,time
assert os.getuid()==1000
roots={'Rlk':Path('/home/admin/light-media-plugins-migration-removelink-20261105'),'SDK':Path('/home/admin/light-media-plugins-migration-sdk98-20261105')}
rootmarkers={'Rlk':'light-media-plugins/RemoveLink/20261105/owned-only','SDK':'light-media-plugins/SDK98/20261105/owned-only'}
for k,r in roots.items():assert not r.is_symlink()and(r/'.task-owned').read_text().strip()==rootmarkers[k]
active=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  raw=(p/'cmdline').read_bytes()
  if any(str(r).encode()in raw for r in roots.values()):active.append(int(p.name))
 except(FileNotFoundError,PermissionError,ProcessLookupError):pass
assert not active,active
keep={'Rlk':{'owned-notice-fixture-linux','remove-link-auth-declarations-linux','remove-link-update-auth-declarations-linux','removelink-business-main-linux.test','removelink-main6-linux.test'},'SDK':{'category-editor-auth-declarations-linux','torrent-transfer-auth-declarations-linux','site-statistic-source-declarations-linux','source-declarations-mp-server-status-linux','source-declarations-plugin-uninstall-linux','source-declarations-plugin-uninstall-2.2.1-linux','source-declarations-owned-pui-fixture-linux','pluginuninstall-current-main-linux.test','light-media-host-managed-storage-linux','light-media-hostf7-linux'}}
known={'Rlk':{'owned-notice-fixture-linux','remove-link-auth-declarations-linux','remove-link-declarations-linux','remove-link-final59-sdk98-linux','remove-link-linux','remove-link-update-auth-declarations-linux','remove-link-update-declarations-linux','remove-link-update-final59-sdk98-linux','remove-link-update-linux','removelink-business-main-linux.test','removelink-main-driver-linux.test','removelink-main4-linux.test','removelink-main6-linux.test'},'SDK':{'category-editor-auth-declarations-linux','category-editor-sdk98-linux-amd64','category-editor-source-declarations-linux','light-media-host-getter-gates-linux','light-media-host-managed-storage-linux','light-media-host-parent0300-linux','light-media-host-pluginuninstall-linux','light-media-host-pluginuninstall-reviewed-linux','light-media-host-state-query-linux','light-media-host-state3a-linux','light-media-host-unlink-linux','light-media-hostf7-linux','mp-server-status-linux-amd64','plugin-uninstall-sdk98-linux-amd64','pluginuninstall-current-main-linux.test','sdk98-impact-main-tests-linux-amd64','site-statistic-sdk98-linux-amd64','site-statistic-source-declarations-linux','source-declarations-mp-server-status-linux','source-declarations-owned-pui-fixture-linux','source-declarations-plugin-uninstall-2.2.1-linux','source-declarations-plugin-uninstall-linux','torrent-transfer-auth-declarations-linux','torrent-transfer-sdk98-linux-amd64','torrent-transfer-source-declarations-linux'}}
for k,r in roots.items():assert {p.name for p in(r/'bin').iterdir()}==known[k]
runtime={'Rlk':[(f'main-run-{i}','light-media-plugins/RemoveLink/ordinary-main/20261105/owned-only')for i in range(1,10)]+[(f'canonical-package-main-{i}','light-media-plugins/RemoveLink/ordinary-main/20261105/owned-only')for i in range(1,4)]+[('business-main-1','light-media-plugins/RemoveLink/ordinary-main/20261105/owned-only')], 'SDK':[(n,'light-media-plugins/SDK98Impact/20261105/owned-only')for n in ['managed-storage-main-four-1','source-auth-main-four-2','source-declarations-main-four-1']]+[(n,'light-media-plugins/PluginUnInstall/20261105/owned-only')for n in ['managed-storage-pui-main-1','source-declarations-pui-main-3']]}
for k,ls in runtime.items():
 for name,marker in ls:
  p=roots[k]/name;assert p.is_dir()and not p.is_symlink()and p.stat().st_uid==1000 and(p/'.task-owned').read_text().strip()==marker
records=[]
for k,r in roots.items():
 for p in sorted((r/'bin').iterdir()):
  assert p.is_file()and not p.is_symlink()and p.stat().st_uid==1000
  data=p.read_bytes();assert data[:4]==b'\x7fELF',p
  row={'path':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'action':'retained_current_compatibility_input' if p.name in keep[k]else'deleted_superseded_generated_ELF'}
  if p.name not in keep[k]:p.unlink()
  records.append(row)
 for name,marker in runtime[k]:
  p=r/name
  # Only this task's synthetic runtime/package dirs; never follow symlinks.
  for parent,dirs,files in os.walk(p,followlinks=False):
   if not Path(parent).is_symlink():os.chmod(parent,0o700)
  shutil.rmtree(p);records.append({'path':str(p),'marker':marker,'action':'deleted_completed_owned_runtime','after_exists':p.exists()})
result={'classification':'owned test runtime/generated artifact cleanup after exact raw archival and independent native DB/PID/input sample; no original system/media/production service changes','uid':os.getuid(),'active_task_processes_before':active,'retention_reason':'one current six-family SDK98 worker set and source version/fixture inputs; latest bounded drivers; current881f host plus one f7 protocol compatibility host for upcoming opt-in SDK acceptance; no running services','records':records,'completed_runtime_dirs_removed':sum(x['action']=='deleted_completed_owned_runtime'for x in records),'superseded_ELFs_removed':sum(x['action']=='deleted_superseded_generated_ELF'for x in records),'retained_ELFs':sum(x['action']=='retained_current_compatibility_input'for x in records)}
(roots['Rlk']/'cleanup-completed-runs-20261106.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
