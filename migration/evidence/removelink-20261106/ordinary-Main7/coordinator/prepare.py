from pathlib import Path
import json,hashlib,subprocess
root=Path.cwd();out=Path(__file__).resolve().parent;peer='admin@192.168.8.129';r='/home/admin/light-media-plugins-migration-removelink-20261105';shared='/home/admin/light-media-plugins-migration-sdk98-20261105';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
producer=root/'work/migration-20261106/source-auth-declaration-addon';seal=producer/'freeze.json';assert sha(seal)=='b2b5e1055cce13b925d7afb6e92d7d9406519906c9a10bbe3c82cf0dfccef52c';freeze=json.loads(seal.read_text())
for f in freeze['products']:assert sha(root/f['path'])==f['sha256'],f['path']
current=producer/'removelink59-auth-epoch.json';assert sha(current)==freeze['Rlk59_sha256']
for f in json.loads(current.read_text()):assert sha(root/f['path'])==f['sha256'],f['path']
old=root/'work/migration-20261105/removelink-main6-20261106';driver=old/'removelink-main6-linux.test';d=json.loads((old/'driver-build-binding.json').read_text());assert sha(driver)==d['binary_sha256']=='f24e9b1fdc9e2649ce94a054c3a485120bc8a6e357595a4d59693063221e054d'
effective={}
for n,h in d['inputs_after'].items():
 actual=root/n
 if sha(actual)!=h:
  assert n=='tests/integration/pluginuninstall_main_test.go';actual=old/'frozen-test-inputs'/n;assert sha(actual)==h;effective[n]=str(actual)
local={producer/'bins/remove-link-linux':r+'/bin/remove-link-auth-declarations-linux',producer/'bins/remove-link-2.18.1-linux':r+'/bin/remove-link-update-auth-declarations-linux'}
inputs={dest:sha(p)for p,dest in local.items()};inputs[shared+'/bin/light-media-host-getter-gates-linux']='3c0513c3c92e4ab15128f1d0c0756cdd4c763403d0dc2b6111f8812a36d1c6cb';inputs[r+'/bin/removelink-main6-linux.test']=sha(driver)
for p in sorted((root/'plugins/removelink/frontend').iterdir()):
 if p.is_file():inputs[r+'/frontend-run4/'+p.name]=sha(p)
setup=f'''from pathlib import Path
import os,hashlib
r=Path({r!r});s=Path({shared!r})
assert os.getuid()==1000 and (r/'.task-owned').read_text().strip()=='light-media-plugins/RemoveLink/20261105/owned-only'
assert (s/'.task-owned').read_text().strip()=='light-media-plugins/SDK98/20261105/owned-only'
assert not (r/'main-run-7').exists()
inputs={inputs!r}
for name,expected in inputs.items():
 if name in {set(local.values())!r}:continue
 p=Path(name);assert not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,name
'''
p=subprocess.run(['ssh',peer,'python3','-'],input=setup.encode(),capture_output=True);assert p.returncode==0,p.stderr.decode()
for p,dest in local.items():subprocess.run(['scp',str(p),peer+':'+dest],check=True,capture_output=True)
p=out/'input-inventory-run7.json';p.write_text(json.dumps(inputs,indent=2)+'\n');subprocess.run(['scp',str(p),peer+':'+r+'/input-inventory-run7.json'],check=True,capture_output=True)
binding={'classification':'fresh current23-declaration Main7; only Auth manifest omissions changed since real Main6; samehost3c05/SDK98/driverf24/three frontend assets and all business implementations','input_sha256':inputs,'driver_original_binding_sha256':sha(old/'driver-build-binding.json'),'driver_effective_single_file_overlay':effective,'producer_auth_freeze_sha256':sha(seal),'current_Rlk59_sha256':sha(current),'independent_auth_review':'d8d7533603ec9a2b7cdfa399789cd29e61141cd25b2b428fbf66e3cd02d2cdc9','independent_host4_review':'966954ce047189e0bf0f5cda0b47ffb79ea3979fa842f8a3601045dc89c8e8ed','minimum_host_commit':'651dd2c3f75f4be74951d0a552f93a9079046e1d','ordinary_main_status':'not_started'};(out/'prepared-input-binding.json').write_text(json.dumps(binding,indent=2)+'\n');print(json.dumps({'inputs':len(inputs),'binding':sha(out/'prepared-input-binding.json'),'status':'prepared_not_started'}))
