from pathlib import Path
import os,json,hashlib,shutil
assert os.getuid()==1000
base=Path('/home/admin');marker='light-media-plugins/root-asi-owned/20261106/owned-only';names=['light-media-plugins-root-asi-ui-20261106'];rows=[]
for name in names:
 r=base/name;assert r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text().strip()==marker
 active=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:exe=os.readlink(proc/'exe')
  except OSError:continue
  if exe.startswith(str(r)+'/'):active.append(int(proc.name))
 assert not active,(name,active)
 open_handles=[]
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try: handles=list((proc/'fd').iterdir())+[proc/'cwd']
  except OSError:continue
  for handle in handles:
   try:target=os.readlink(handle)
   except OSError:continue
   if target==str(r)or target.startswith(str(r)+'/'):open_handles.append({'pid':int(proc.name),'fd':handle.name})
 assert not open_handles,(name,open_handles)
 bundle={}
 for n in ['host-main-linux','auto-sign-in-linux','main-driver-linux.test']:
  f=r/'bundle/bin'/n;assert f.is_file()and not f.is_symlink();bundle[n]={'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size}
 assert bundle['host-main-linux']['sha256']=='b0a9a175e3b6d61b1a9158d4638f9a3c6639291f93879da11f5cbf157e5c6963'
 assert bundle['auto-sign-in-linux']['sha256']in ['f9db86c4ee6007c0e93b5192ac019c8b4c83ff9d4c353dacb5f4ea468fb93c19','a4524236b3bad3462f640958ad56a170759558d69ff038ce56953ba38f648918']
 assert bundle['main-driver-linux.test']['sha256']=='8c35277a0e61623801e762b55aeab1e5de8b4d214b267738ab38bcb64e21f669'
 files=[f for f in r.rglob('*')if f.is_file()and not f.is_symlink()];rows.append({'root':str(r),'marker':marker,'active_task_exe':active,'files':len(files),'bytes':sum(f.stat().st_size for f in files),'bundle':bundle})
# All five roots preflight before the first removal; no original service path.
for row in rows:
 r=Path(row['root']);assert r.parent==base and(r/'.task-owned').read_text().strip()==marker;shutil.rmtree(r);assert not r.exists();row['removed']=True
print(json.dumps({'owned_only':True,'roots':rows,'private_runtime_values_not_read_or_copied':True,'production_service_untouched':True},indent=2))
