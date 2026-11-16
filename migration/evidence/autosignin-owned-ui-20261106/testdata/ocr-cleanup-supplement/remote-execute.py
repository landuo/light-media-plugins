from pathlib import Path
import json,hashlib,subprocess,os,datetime
phases=[{'provenance_path': '/Users/accidia/projects/light-media-plugins/work/source-ocr-value-domain-20261106/binary-provenance.json', 'provenance_sha256': 'ff0f94c45f0bd8c39cc4f82ad6c341e71dceda2a4117b81ab96e0f1c1388b6a0', 'root': '/home/admin/light-media-plugins-source-ocr-value-domain-20261106', 'marker': 'light-media-plugins/source-ocr-value-domain/20261106/owned-only', 'label': 'lm-source-ocr-value-domain-20261106', 'files': [{'relative': 'bundle/bin/domain-app-linux.test', 'sha256': 'e4d76ef2d679eb57effb9b27054b2e5f9beefefb8a2b4acffec81e381ed4d566', 'bytes': 71245986}, {'relative': 'bundle/bin/new-domain-probe-linux', 'sha256': '8312f26e11bb5ffc97074671cd61c2466a66b37821754ee97a7a0e01970fd213', 'bytes': 12406946}, {'relative': 'bundle/bin/old-parser-domain-probe-linux', 'sha256': 'b679a7a9299e5fbf9872d5b3561b478159475479d7108c74e70be8426b2c2002', 'bytes': 12406946}, {'relative': 'bundle/bin/old-binding-domain-probe-linux', 'sha256': '43e84dadeac8cfb8d1ebc4e3a9159e09ff382d585026d539173dbf52df236fa1', 'bytes': 12406946}]}, {'provenance_path': '/Users/accidia/projects/light-media-plugins/work/source-ocr-json-integrated-20261106/binary-provenance.json', 'provenance_sha256': 'b6deafee4a0413d50b8679f99f64cb57d5552de924b87ebc2097289800955fd9', 'root': '/home/admin/light-media-plugins-source-ocr-json-integrated-20261106', 'marker': 'light-media-plugins/source-ocr-json-integrated/20261106/owned-only', 'label': 'lm-source-ocr-json-integrated-20261106', 'files': [{'relative': 'bundle/bin/current-domain-probe-linux', 'sha256': 'f1a16ca4a0e6080e35e2c269b5893f11e5b191f596e0495e50b8432c9f7efeed', 'bytes': 12406946}, {'relative': 'bundle/bin/current-domain-app-linux.test', 'sha256': '8cf0f9e2e8b078b790694f6f6870ab67c203a44c64e36181053066d6ca30efd4', 'bytes': 71245986}]}]
results=[]
for phase in phases:
 r=Path(phase['root']);assert r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text().strip()==phase['marker']
 result={'root':str(r),'label':phase['label'],'marker_equal':True,'deleted':[]}
 for row in phase['files']:
  p=r/row['relative'];assert p.is_file()and not p.is_symlink()and p.resolve().is_relative_to(r.resolve());assert p.stat().st_size==row['bytes']and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
 labels=subprocess.run(['docker','ps','-aq','--filter','label=task='+phase['label']],capture_output=True);assert labels.returncode==0 and not labels.stdout.strip();result['own_containers']=0
 held=[]
 for d in Path('/proc').iterdir():
  if not d.name.isdigit():continue
  for key in ['exe','cwd']:
   try:
    target=os.readlink(d/key)
    if target==str(r)or target.startswith(str(r)+'/'):held.append({'pid':d.name,'kind':key,'path':target})
   except OSError:pass
  try:fds=list((d/'fd').iterdir())
  except OSError:continue
  for fd in fds:
   try:
    target=os.readlink(fd)
    if target==str(r)or target.startswith(str(r)+'/'):held.append({'pid':d.name,'kind':'fd','path':target})
   except OSError:pass
 assert not held,held;result['proc_exe_cwd_fd_matches']=[]
 for row in phase['files']:
  p=r/row['relative'];p.unlink();assert not p.exists();result['deleted'].append(row)
 result['bytes_deleted']=sum(x['bytes']for x in result['deleted']);results.append(result)
print(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'only exact owned released JSON ELF files; source/oracles/raw/frozen manifests and recipes untouched','results':results},ensure_ascii=False))
