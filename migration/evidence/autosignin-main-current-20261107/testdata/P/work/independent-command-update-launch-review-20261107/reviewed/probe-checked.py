CONFIG={'root': '/home/admin/light-media-plugins-root-asi-native-20261107', 'marker': 'light-media-plugins/root-asi-native/20261107/owned-only', 'name': 'lm-root-asi-native-20261107', 'bom': {'bin/host': {'sha256': '8ea38cff7e98f6a1eb7089f7ff04cc8c56fdb41baedfdbc843db13824b999f67', 'bytes': 57217186}, 'bin/worker': {'sha256': '2b77bc3db6c80ff67314a68daa0df90b1595e99ab2bc658ca80cfaafd6a251a0', 'bytes': 12796066}, 'bin/worker-updated': {'sha256': 'e38f19188cfbfe4b295893b9707c1ba8ee77117880ffdcfb7952e77bf0108f36', 'bytes': 12796066}, 'bin/cli': {'sha256': '525e34407b50f4bd38e16d29bfe4d775c8052504f40072789cc8a4b43f4cf1b8', 'bytes': 25215138}, 'bin/driver': {'sha256': 'f725924537c0d650802d4626166e02f8249401f782dcb154bdcf51ee8399d1e8', 'bytes': 9748642}}}
from pathlib import Path
import json,subprocess,os,hashlib
r=Path(CONFIG['root'])
assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
assert not (r/'owned-r3').exists()and not(r/'attempt4').exists()
assert not subprocess.check_output(['docker','ps','-aq','--filter','name=^/'+CONFIG['name']+'$']).strip()
changed=[]
for n,row in CONFIG['bom'].items():
 f=r/'bundle'/n
 assert n in ['bin/host','bin/worker','bin/worker-updated','bin/cli','bin/driver']and not f.is_symlink()
 if not f.exists():
  assert n=='bin/worker-updated'and f.parent.is_dir()and not f.parent.is_symlink();changed.append(n);continue
 assert f.is_file()
 if hashlib.sha256(f.read_bytes()).hexdigest()!=row['sha256']:changed.append(n)
print(json.dumps({'changed':changed}))
