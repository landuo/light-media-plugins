from pathlib import Path
import os,subprocess,json,hashlib
r=Path('/home/admin/light-media-plugins-root-asi-native-20261107')
assert os.getuid()==1000 and r.is_dir() and not r.is_symlink() and (r/'.task-owned').read_text()=='light-media-plugins/root-asi-native/20261107/owned-only'
assert not list((r/'owned/runtime').iterdir())
assert not any((r/n).exists() for n in ['actual.stdout','actual.stderr','command.json'])
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+'lm-root-asi-native-20261107'+'$']).strip()
bom={'bin/host': {'sha256': '062da6f0e5f5814dc4f60ac8bb30c7240c2d71b940cc4250261cdf97bed136fb', 'bytes': 57200802}, 'bin/worker': {'sha256': '02ece64a7ecb85c64b126279014d026d5684591cd19237b24e12af8108481269', 'bytes': 12779682}, 'bin/cli': {'sha256': '72ee655a8aa706fa487201047bba360902886828d608f4efac31a40e0f8d5865', 'bytes': 25215138}, 'bin/driver': {'sha256': '97e544e53901c666d9654e237cd09079ac5040a2918bfa46f90ca37610e030ef', 'bytes': 9707682}}
for n,row in bom.items():
 p=r/'bundle'/n; assert p.is_file() and not p.is_symlink() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
