CONFIG={'root': '/home/admin/light-media-plugins-root-asi-native-20261107', 'marker': 'light-media-plugins/root-asi-native/20261107/owned-only', 'name': 'lm-root-asi-native-20261107', 'bom': {'bin/host': {'sha256': 'c31f8f43480a3cf297598af401eaa16899f65aa2b5b09fe138545613334c42c6', 'bytes': 57225378}, 'bin/worker': {'sha256': '2b77bc3db6c80ff67314a68daa0df90b1595e99ab2bc658ca80cfaafd6a251a0', 'bytes': 12796066}, 'bin/worker-updated': {'sha256': 'e38f19188cfbfe4b295893b9707c1ba8ee77117880ffdcfb7952e77bf0108f36', 'bytes': 12796066}, 'bin/cli': {'sha256': '7044b75a4cb61768538c0dcf764ef6a038254edb75f820b46ace98035abe0c84', 'bytes': 25215138}, 'bin/driver': {'sha256': '75fe4f1ecddc27f3249d2ec8266798ff34cfcb596cbe1f0d9f9a056dd85d637f', 'bytes': 9756834}}}
from pathlib import Path
import json,subprocess,os,hashlib
r=Path(CONFIG['root'])
assert os.getuid()==1000 and r.is_dir()and not r.is_symlink()and(r/'.task-owned').read_text()==CONFIG['marker']
assert not (r/'owned-r5').exists()and not(r/'attempt6').exists()
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
